# Переосмысление HTTP-обработчиков

[**Весь код можно найти здесь**](https://github.com/quii/learn-go-with-tests/tree/main/q-and-a/http-handlers-revisited)

В этой книге уже есть глава о [тестировании HTTP-обработчика](http-server.md), но здесь будет более широкое обсуждение их проектирования, чтобы их было просто тестировать.

Мы рассмотрим реальный пример и то, как мы можем улучшить его проектирование, применяя такие принципы, как принцип единственной ответственности и разделение ответственности. Эти принципы могут быть реализованы с помощью [интерфейсов](structs-methods-and-interfaces.md) и [внедрения зависимостей](dependency-injection.md). Таким образом, мы покажем, насколько тривиальным на самом деле является тестирование обработчиков.

![Common question in Go community illustrated](.gitbook/assets/amazing-art.png)

Тестирование HTTP-обработчиков, кажется, является повторяющимся вопросом в сообществе Go, и я думаю, что это указывает на более широкую проблему непонимания того, как их проектировать.

Так часто трудности людей с тестированием проистекают из дизайна их кода, а не из фактического написания тестов. Как я часто подчеркиваю в этой книге:

> Если ваши тесты доставляют вам боль, прислушайтесь к этому сигналу и подумайте о дизайне вашего кода.

## Пример

[Сантош Кумар написал мне в Твиттере](https://twitter.com/sntshk/status/1255559003339284481)

> Как мне протестировать http-обработчик, у которого есть зависимость от mongodb?

Вот код

```go
func Registration(w http.ResponseWriter, r *http.Request) {
	var res model.ResponseResult
	var user model.User

	w.Header().Set("Content-Type", "application/json")

	jsonDecoder := json.NewDecoder(r.Body)
	jsonDecoder.DisallowUnknownFields()
	defer r.Body.Close()

	// check if there is proper json body or error
	if err := jsonDecoder.Decode(&user); err != nil {
		res.Error = err.Error()
		// return 400 status codes
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(res)
		return
	}

	// Connect to mongodb
	client, _ := mongo.NewClient(options.Client().ApplyURI("mongodb://127.0.0.1:27017"))
	ctx, _ := context.WithTimeout(context.Background(), 10*time.Second)
	err := client.Connect(ctx)
	if err != nil {
		panic(err)
	}
	defer client.Disconnect(ctx)
	// Check if username already exists in users datastore, if so, 400
	// else insert user right away
	collection := client.Database("test").Collection("users")
	filter := bson.D{{"username", user.Username}}
	var foundUser model.User
	err = collection.FindOne(context.TODO(), filter).Decode(&foundUser)
	if foundUser.Username == user.Username {
		res.Error = UserExists
		// return 400 status codes
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(res)
		return
	}

	pass, err := bcrypt.GenerateFromPassword([]byte(user.Password), bcrypt.DefaultCost)
	if err != nil {
		res.Error = err.Error()
		// return 400 status codes
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(res)
		return
	}
	user.Password = string(pass)

	insertResult, err := collection.InsertOne(context.TODO(), user)
	if err != nil {
		res.Error = err.Error()
		// return 400 status codes
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(res)
		return
	}

	// return 200
	w.WriteHeader(http.StatusOK)
	res.Result = fmt.Sprintf("%s: %s", UserCreated, insertResult.InsertedID)
	json.NewEncoder(w).Encode(res)
	return
}
```

Давайте просто перечислим всё, что должна делать эта одна функция:

1.  Записывать HTTP-ответы, отправлять заголовки, коды состояния и т.д.
2.  Декодировать тело запроса в `User`
3.  Подключаться к базе данных (и все сопутствующие детали)
4.  Запрашивать базу данных и применять некоторую бизнес-логику в зависимости от результата
5.  Генерировать пароль
6.  Вставлять запись

Это слишком много.

## Что такое HTTP-обработчик и что он должен делать?

Забыв на мгновение о специфике Go, независимо от того, на каком языке я работал, мне всегда помогало размышление о [разделении ответственности](https://en.wikipedia.org/wiki/Separation_of_concerns) и [принципе единственной ответственности](https://en.wikipedia.org/wiki/Single-responsibility_principle).

Это может быть довольно сложно применить в зависимости от решаемой проблемы. Что именно _является_ ответственностью?

Границы могут стираться в зависимости от того, насколько абстрактно вы мыслите, и иногда ваша первая догадка может быть неверной.

К счастью, с HTTP-обработчиками у меня довольно хорошее представление о том, что они должны делать, независимо от того, над каким проектом я работал:

1.  Принимать HTTP-запрос, разбирать и проверять его.
2.  Вызвать некий `ServiceThing` для выполнения `ImportantBusinessLogic` с данными, полученными на шаге 1.
3.  Отправить соответствующий `HTTP`-ответ в зависимости от того, что возвращает `ServiceThing`.

Я не говорю, что каждый HTTP-обработчик _вообще_ должен иметь примерно такую форму, но в 99 случаях из 100 это кажется мне верным.

Когда вы разделяете эти ответственности:

*   Тестирование обработчиков становится легким и сосредоточено на небольшом числе задач.
*   Важно, что тестирование `ImportantBusinessLogic` больше не должно касаться `HTTP`, вы можете чисто тестировать бизнес-логику.
*   Вы можете использовать `ImportantBusinessLogic` в других контекстах, не изменяя его.
*   Если `ImportantBusinessLogic` меняет свое поведение, пока интерфейс остается прежним, вам не придется менять обработчики.

## Обработчики Go

[`http.HandlerFunc`](https://golang.org/pkg/net/http/#HandlerFunc)

> Тип HandlerFunc является адаптером, позволяющим использовать обычные функции в качестве HTTP-обработчиков.

`type HandlerFunc func(ResponseWriter, *Request)`

Читатель, передохните и взгляните на код выше. Что вы заметили?

**Это функция, которая принимает некоторые аргументы**

Здесь нет магии фреймворка, аннотаций, волшебных бобов, ничего.

Это просто функция, _и мы знаем, как тестировать функции_.

Это хорошо согласуется с приведенным выше комментарием:

*   Он принимает [`http.Request`](https://golang.org/pkg/net/http/#Request), который представляет собой просто набор данных для проверки, разбора и валидации.
*   > [Интерфейс `http.ResponseWriter` используется HTTP-обработчиком для построения HTTP-ответа.](https://golang.org/pkg/net/http/#ResponseWriter)

### Супер базовый пример теста

```go
func Teapot(res http.ResponseWriter, req *http.Request) {
	res.WriteHeader(http.StatusTeapot)
}

func TestTeapotHandler(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	res := httptest.NewRecorder()

	Teapot(res, req)

	if res.Code != http.StatusTeapot {
		t.Errorf("got status %d but wanted %d", res.Code, http.StatusTeapot)
	}
}
```

Чтобы протестировать нашу функцию, мы _вызываем_ ее.

Для нашего теста мы передаем `httptest.ResponseRecorder` в качестве аргумента `http.ResponseWriter`, и наша функция будет использовать его для записи `HTTP`-ответа. Рекордер запишет (или _проследит_) то, что было отправлено, а затем мы можем сделать наши утверждения.

## Вызов `ServiceThing` в нашем обработчике

Распространенная жалоба на учебники по TDD заключается в том, что они всегда "слишком просты" и недостаточно "реальны". Мой ответ на это:

> Разве не было бы прекрасно, если бы весь ваш код был прост для чтения и тестирования, как примеры, которые вы упоминаете?

Это одна из самых больших проблем, с которыми мы сталкиваемся, но к которой нужно постоянно стремиться. _Возможно_ (хотя и не обязательно легко) спроектировать код таким образом, чтобы его было просто читать и тестировать, если мы практикуем и применяем хорошие принципы разработки программного обеспечения.

Вспомним, что делал предыдущий обработчик:

1.  Записывать HTTP-ответы, отправлять заголовки, коды состояния и т.д.
2.  Декодировать тело запроса в `User`
3.  Подключаться к базе данных (и все сопутствующие детали)
4.  Запрашивать базу данных и применять некоторую бизнес-логику в зависимости от результата
5.  Генерировать пароль
6.  Вставлять запись

Применяя идею более идеального разделения ответственности, я бы хотел, чтобы это выглядело так:

1.  Декодировать тело запроса в `User`
2.  Вызвать `UserService.Register(user)` (это наш `ServiceThing`)
3.  Если возникает ошибка, отреагировать на нее (пример всегда отправляет `400 BadRequest`, что, по моему мнению, неверно), я пока что буду использовать универсальный обработчик `500 Internal Server Error`. Я должен подчеркнуть, что возврат `500` для всех ошибок делает API ужасным! Позже мы сможем сделать обработку ошибок более сложной, возможно, с помощью [типов ошибок](error-types.md).
4.  Если ошибок нет, `201 Created` с ID в теле ответа (опять же, для краткости/лени)

Ради краткости я не буду рассматривать обычный процесс TDD, примеры смотрите во всех других главах.

### Новый дизайн

```go
type UserService interface {
	Register(user User) (insertedID string, err error)
}

type UserServer struct {
	service UserService
}

func NewUserServer(service UserService) *UserServer {
	return &UserServer{service: service}
}

func (u *UserServer) RegisterUser(w http.ResponseWriter, r *http.Request) {
	defer r.Body.Close()

	// request parsing and validation
	var newUser User
	err := json.NewDecoder(r.Body).Decode(&newUser)

	if err != nil {
		http.Error(w, fmt.Sprintf("could not decode user payload: %v", err), http.StatusBadRequest)
		return
	}

	// call a service thing to take care of the hard work
	insertedID, err := u.service.Register(newUser)

	// depending on what we get back, respond accordingly
	if err != nil {
		//todo: handle different kinds of errors differently
		http.Error(w, fmt.Sprintf("problem registering new user: %v", err), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusCreated)
	fmt.Fprint(w, insertedID)
}
```

Наш метод `RegisterUser` соответствует форме `http.HandlerFunc`, так что мы готовы к работе. Мы присоединили его как метод к новому типу `UserServer`, который содержит зависимость от `UserService`, представленную в виде интерфейса.

Интерфейсы — это фантастический способ обеспечить, чтобы наши `HTTP`-задачи были отделены от любой конкретной реализации; мы можем просто вызвать метод на зависимости, и нам не нужно беспокоиться о том, _как_ регистрируется пользователь.

Если вы хотите более подробно изучить этот подход, следуя TDD, прочитайте главу [Внедрение зависимостей](dependency-injection.md) и главу [HTTP-сервер раздела "Создание приложения"](http-server.md).

Теперь, когда мы отделились от любых конкретных деталей реализации, связанных с регистрацией, написание кода для нашего обработчика становится простым и соответствует ранее описанным обязанностям.

### Тесты!

Эта простота отражается в наших тестах.

```go
type MockUserService struct {
	RegisterFunc    func(user User) (string, error)
	UsersRegistered []User
}

func (m *MockUserService) Register(user User) (insertedID string, err error) {
	m.UsersRegistered = append(m.UsersRegistered, user)
	return m.RegisterFunc(user)
}

func TestRegisterUser(t *testing.T) {
	t.Run("can register valid users", func(t *testing.T) {
		user := User{Name: "CJ"}
		expectedInsertedID := "whatever"

		service := &MockUserService{
			RegisterFunc: func(user User) (string, error) {
				return expectedInsertedID, nil
			},
		}
		server := NewUserServer(service)

		req := httptest.NewRequest(http.MethodGet, "/", userToJSON(user))
		res := httptest.NewRecorder()

		server.RegisterUser(res, req)

		assertStatus(t, res.Code, http.StatusCreated)

		if res.Body.String() != expectedInsertedID {
			t.Errorf("expected body of %q but got %q", res.Body.String(), expectedInsertedID)
		}

		if len(service.UsersRegistered) != 1 {
			t.Fatalf("expected 1 user added but got %d", len(service.UsersRegistered))
		}

		if !reflect.DeepEqual(service.UsersRegistered[0], user) {
			t.Errorf("the user registered %+v was not what was expected %+v", service.UsersRegistered[0], user)
		}
	})

	t.Run("returns 400 bad request if body is not valid user JSON", func(t *testing.T) {
		server := NewUserServer(nil)

		req := httptest.NewRequest(http.MethodGet, "/", strings.NewReader("trouble will find me"))
		res := httptest.NewRecorder()

		server.RegisterUser(res, req)

		assertStatus(t, res.Code, http.StatusBadRequest)
	})

	t.Run("returns a 500 internal server error if the service fails", func(t *testing.T) {
		user := User{Name: "CJ"}

		service := &MockUserService{
			RegisterFunc: func(user User) (string, error) {
				return "", errors.New("couldn't add new user")
			},
		}
		server := NewUserServer(service)

		req := httptest.NewRequest(http.MethodGet, "/", userToJSON(user))
		res := httptest.NewRecorder()

		server.RegisterUser(res, req)

		assertStatus(t, res.Code, http.StatusInternalServerError)
	})
}
```

Теперь, когда наш обработчик не связан с конкретной реализацией хранилища, нам тривиально написать `MockUserService`, чтобы помочь нам создавать простые, быстрые модульные тесты для проверки его конкретных обязанностей.

### А как насчет кода базы данных? Вы жульничаете!

Всё это очень обдуманно. Мы не хотим, чтобы HTTP-обработчики занимались нашей бизнес-логикой, базами данных, соединениями и т.д.

Таким образом, мы освободили обработчик от беспорядочных деталей, а также _упростили_ тестирование нашего слоя сохранения данных и бизнес-логики, поскольку он также больше не связан с нерелевантными HTTP-деталями.

Всё, что нам нужно сделать, это реализовать наш `UserService` с использованием любой базы данных, которую мы хотим использовать

```go
type MongoUserService struct {
}

func NewMongoUserService() *MongoUserService {
	//todo: pass in DB URL as argument to this function
	//todo: connect to db, create a connection pool
	return &MongoUserService{}
}

func (m MongoUserService) Register(user User) (insertedID string, err error) {
	// use m.mongoConnection to perform queries
	panic("implement me")
}
```

Мы можем протестировать это отдельно, и как только будем довольны в `main`, мы можем соединить эти два блока вместе для нашего работающего приложения.

```go
func main() {
	mongoService := NewMongoUserService()
	server := NewUserServer(mongoService)
	http.ListenAndServe(":8000", http.HandlerFunc(server.RegisterUser))
}
```

### Более надежный и расширяемый дизайн с небольшими усилиями

Эти принципы не только облегчают нашу жизнь в краткосрочной перспективе, но и облегчают расширение системы в будущем.

Было бы неудивительно, если бы в дальнейших итерациях этой системы мы захотели отправлять пользователю электронное письмо с подтверждением регистрации.

При старом дизайне нам пришлось бы менять обработчик _и_ окружающие тесты. Часто именно так части кода становятся неподдерживаемыми: все больше и больше функциональности проникает в них, потому что они уже _спроектированы_ таким образом; чтобы "HTTP-обработчик" обрабатывал... всё!

Разделяя ответственности с помощью интерфейса, нам не нужно _совсем_ редактировать обработчик, потому что он не занимается бизнес-логикой, связанной с регистрацией.

## Подведение итогов

Тестирование HTTP-обработчиков Go не является сложной задачей, но проектирование хорошего программного обеспечения может быть таковым!

Люди ошибочно считают HTTP-обработчики чем-то особенным и отбрасывают хорошие практики проектирования программного обеспечения при их написании, что затем делает их тестирование сложным.

Повторяю еще раз: **HTTP-обработчики Go — это просто функции**. Если вы пишете их так же, как и другие функции, с четкими обязанностями и хорошим разделением ответственности, у вас не возникнет проблем с их тестированием, и ваша кодовая база станет от этого здоровее.
---