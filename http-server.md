# HTTP-сервер

**[Весь код для этой главы вы можете найти здесь](https://github.com/quii/learn-go-with-tests/tree/main/http-server)**

Вам было предложено создать веб-сервер, на котором пользователи смогут отслеживать, сколько игр выиграли игроки.

-   `GET /players/{name}` должен возвращать число, указывающее общее количество побед.
-   `POST /players/{name}` должен регистрировать победу для этого имени, увеличивая счетчик при каждом последующем `POST`.

Мы будем следовать подходу TDD, как можно быстрее создавая работающее программное обеспечение, а затем вносить небольшие итеративные улучшения, пока не получим решение. Используя этот подход, мы:

-   Поддерживаем небольшой объем проблемного пространства в любой момент времени.
-   Не уходим в дебри.
-   Если мы застрянем или потеряемся, откат не приведет к потере большого объема работы.

## Красный, зеленый, рефакторинг

На протяжении всей этой книги мы подчеркивали процесс TDD: написание теста и наблюдение за его провалом (красный), написание *минимального* количества кода для его работы (зеленый) и затем рефакторинг.

Эта дисциплина написания минимального количества кода важна с точки зрения безопасности, которую дает TDD. Вы должны стремиться выйти из "красной" зоны как можно скорее.

Кент Бек описывает это так:

> Заставьте тест работать быстро, совершая в процессе любые необходимые грехи.

Вы можете совершать эти грехи, потому что впоследствии вы проведете рефакторинг, опираясь на безопасность тестов.

### Что, если вы этого не сделаете?

Чем больше изменений вы вносите, находясь в "красной" зоне, тем выше вероятность добавления новых проблем, не покрытых тестами.

Идея состоит в том, чтобы итеративно писать полезный код небольшими шагами, руководствуясь тестами, чтобы не застрять на несколько часов.

### Что раньше: курица или яйцо?

Как мы можем наращивать это инкрементально? Мы не можем выполнить `GET` игрока, не сохранив что-либо, и, кажется, трудно понять, сработал ли `POST` без уже существующей конечной точки `GET`.

Вот где *мокирование* проявляет себя наилучшим образом.

-   `GET` потребуется *нечто*, называемое `PlayerStore`, для получения результатов игрока. Это должен быть интерфейс, чтобы при тестировании мы могли создать простой заглушку для проверки нашего кода, не требуя реализации какого-либо фактического кода хранения.
-   Для `POST` мы можем *шпионить* за его вызовами к `PlayerStore`, чтобы убедиться, что он правильно сохраняет игроков. Наша реализация сохранения не будет связана с получением данных.
-   Чтобы быстро получить работающее программное обеспечение, мы можем создать очень простую реализацию в памяти, а затем, позже, создать реализацию, поддерживаемую любым механизмом хранения, который мы предпочитаем.

## Сначала напишите тест

Мы можем написать тест и заставить его пройти, возвращая жестко заданное значение, чтобы начать работу. Кент Бек называет это "притворством". Как только у нас будет работающий тест, мы сможем написать больше тестов, чтобы помочь нам избавиться от этой константы.

Делая этот очень маленький шаг, мы можем сделать важный старт, заставив общую структуру проекта работать правильно, не слишком беспокоясь о нашей логике приложения.

Для создания веб-сервера в Go вы обычно вызываете [ListenAndServe](https://golang.org/pkg/net/http/#ListenAndServe).

```go
func ListenAndServe(addr string, handler Handler) error
```

Это запустит веб-сервер, слушающий на порту, создавая горутину для каждого запроса и запуская ее на [`Handler`](https://golang.org/pkg/net/http/#Handler).

```go
type Handler interface {
	ServeHTTP(ResponseWriter, *Request)
}
```

Тип реализует интерфейс Handler, реализуя метод `ServeHTTP`, который ожидает два аргумента: первый — это место, куда мы *записываем наш ответ*, а второй — это HTTP-запрос, отправленный на сервер.

Давайте создадим файл с именем `server_test.go` и напишем тест для функции `PlayerServer`, которая принимает эти два аргумента. Отправленный запрос будет на получение счета игрока, который, как мы ожидаем, будет `"20"`.
```go
func TestGETPlayers(t *testing.T) {
	t.Run("returns Pepper's score", func(t *testing.T) {
		request, _ := http.NewRequest(http.MethodGet, "/players/Pepper", nil)
		response := httptest.NewRecorder()

		PlayerServer(response, request)

		got := response.Body.String()
		want := "20"

		if got != want {
			t.Errorf("got %q, want %q", got, want)
		}
	})
}
```

Чтобы протестировать наш сервер, нам понадобится `Request` для отправки, и мы захотим *шпионить* за тем, что наш обработчик записывает в `ResponseWriter`.

-   Мы используем `http.NewRequest` для создания запроса. Первый аргумент — это метод запроса, а второй — путь запроса. Аргумент `nil` относится к телу запроса, который в данном случае нам не нужно устанавливать.
-   `net/http/httptest` уже имеет готовый шпион для нас, называемый `ResponseRecorder`, поэтому мы можем использовать его. У него есть много полезных методов для проверки того, что было записано в качестве ответа.

## Попытайтесь запустить тест

`./server_test.go:13:2: undefined: PlayerServer`

## Напишите минимальное количество кода, чтобы тест запустился и проверьте вывод неудачного теста

Компилятор здесь, чтобы помочь, просто слушайте его.

Создайте файл с именем `server.go` и определите `PlayerServer`.

```go
func PlayerServer() {}
```

Попробуйте снова

```
./server_test.go:13:14: too many arguments in call to PlayerServer
    have (*httptest.ResponseRecorder, *http.Request)
    want ()
```

Добавьте аргументы в нашу функцию

```go
import "net/http"

func PlayerServer(w http.ResponseWriter, r *http.Request) {

}
```

Код теперь компилируется, и тест падает.

```
=== RUN   TestGETPlayers/returns_Pepper's_score
    --- FAIL: TestGETPlayers/returns_Pepper's_score (0.00s)
        server_test.go:20: got '', want '20'
```

## Напишите достаточно кода, чтобы он прошел

Из главы про DI мы затронули HTTP-серверы с функцией `Greet`. Мы узнали, что `ResponseWriter` из `net/http` также реализует `io.Writer`, поэтому мы можем использовать `fmt.Fprint` для отправки строк в качестве HTTP-ответов.

```go
func PlayerServer(w http.ResponseWriter, r *http.Request) {
	fmt.Fprint(w, "20")
}
```

Тест теперь должен пройти.

## Завершите каркас

Мы хотим подключить это к приложению. Это важно, потому что:

-   У нас будет *действительно работающее программное обеспечение*, мы не хотим писать тесты ради тестов, хорошо видеть код в действии.
-   По мере рефакторинга нашего кода, вероятно, мы изменим структуру программы. Мы хотим убедиться, что это отражено и в нашем приложении как часть инкрементального подхода.

Создайте новый файл `main.go` для нашего приложения и поместите в него этот код:

```go
package main

import (
	"log"
	"net/http"
)

func main() {
	handler := http.HandlerFunc(PlayerServer)
	log.Fatal(http.ListenAndServe(":5000", handler))
}
```

До сих пор весь наш код приложения находился в одном файле, однако это не лучшая практика для больших проектов, где вы захотите разделить вещи на разные файлы.

Чтобы запустить это, выполните `go build`, который возьмет все файлы `.go` в каталоге и соберет вам программу. Затем вы можете выполнить ее с помощью `./myprogram`.

### `http.HandlerFunc`

Ранее мы выяснили, что интерфейс `Handler` — это то, что нам нужно реализовать для создания сервера. *Обычно* мы делаем это, создавая `структуру` и заставляя ее реализовать интерфейс, реализуя свой собственный метод `ServeHTTP`. Однако вариант использования структур — это хранение данных, но *в настоящее время* у нас нет состояния, поэтому создавать ее кажется неправильным.

[HandlerFunc](https://golang.org/pkg/net/http/#HandlerFunc) позволяет нам избежать этого.

> Тип HandlerFunc является адаптером, позволяющим использовать обычные функции в качестве HTTP-обработчиков. Если f — это функция с соответствующей сигнатурой, HandlerFunc(f) — это Handler, который вызывает f.

```go
type HandlerFunc func(ResponseWriter, *Request)
```

Из документации мы видим, что тип `HandlerFunc` уже реализовал метод `ServeHTTP`.
Приведя нашу функцию `PlayerServer` к этому типу, мы теперь реализовали требуемый `Handler`.

### `http.ListenAndServe(":5000"...)`

`ListenAndServe` принимает порт для прослушивания и `Handler`. Если возникает проблема, веб-сервер вернет ошибку, например, если порт уже занят. По этой причине мы оборачиваем вызов в `log.Fatal`, чтобы регистрировать ошибку пользователю.

Теперь мы напишем *еще один* тест, чтобы заставить себя внести позитивное изменение и отойти от жестко заданного значения.

## Сначала напишите тест

Мы добавим еще один подтест в наш набор, который попытается получить счет другого игрока, что сломает наш подход с жестко заданным значением.

```go
t.Run("returns Floyd's score", func(t *testing.T) {
	request, _ := http.NewRequest(http.MethodGet, "/players/Floyd", nil)
	response := httptest.NewRecorder()

	PlayerServer(response, request)

	got := response.Body.String()
	want := "10"

	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
})
```

Возможно, вы думали:

> Конечно, нам нужна какая-то концепция хранилища, чтобы контролировать, какой игрок получает какой счет. Странно, что значения в наших тестах кажутся такими произвольными.

Помните, мы просто пытаемся делать как можно меньшие шаги, поэтому пока что мы просто пытаемся сломать константу.

## Попытайтесь запустить тест

```
=== RUN   TestGETPlayers/returns_Pepper's_score
    --- PASS: TestGETPlayers/returns_Pepper's_score (0.00s)
=== RUN   TestGETPlayers/returns_Floyd's_score
    --- FAIL: TestGETPlayers/returns_Floyd's_score (0.00s)
        server_test.go:34: got '20', want '10'
```

## Напишите достаточно кода, чтобы он прошел

```go
//server.go
func PlayerServer(w http.ResponseWriter, r *http.Request) {
	player := strings.TrimPrefix(r.URL.Path, "/players/")

	if player == "Pepper" {
		fmt.Fprint(w, "20")
		return
	}

	if player == "Floyd" {
		fmt.Fprint(w, "10")
		return
	}
}
```

Этот тест заставил нас фактически посмотреть на URL запроса и принять решение. Таким образом, хотя в наших головах мы, возможно, беспокоились о хранилищах игроков и интерфейсах, следующий логический шаг фактически касается *маршрутизации*.

Если бы мы начали с кода хранилища, объем изменений, которые нам пришлось бы внести, был бы очень большим по сравнению с этим. **Это меньший шаг к нашей конечной цели, и он был вызван тестами**.

Мы сопротивляемся искушению использовать какие-либо библиотеки маршрутизации прямо сейчас, только самый маленький шаг, чтобы наш тест прошел.

`r.URL.Path` возвращает путь запроса, который мы затем можем использовать [`strings.TrimPrefix`](https://golang.org/pkg/strings/#TrimPrefix) для удаления `/players/`, чтобы получить запрошенного игрока. Это не очень надежно, но пока сойдет.

## Рефакторинг

Мы можем упростить `PlayerServer`, выделив получение счета в отдельную функцию.

```go
//server.go
func PlayerServer(w http.ResponseWriter, r *http.Request) {
	player := strings.TrimPrefix(r.URL.Path, "/players/")

	fmt.Fprint(w, GetPlayerScore(player))
}

func GetPlayerScore(name string) string {
	if name == "Pepper" {
		return "20"
	}

	if name == "Floyd" {
		return "10"
	}

	return ""
}
```

И мы можем устранить дублирование части кода в тестах, создав вспомогательные функции.

```go
//server_test.go
func TestGETPlayers(t *testing.T) {
	t.Run("returns Pepper's score", func(t *testing.T) {
		request := newGetScoreRequest("Pepper")
		response := httptest.NewRecorder()

		PlayerServer(response, request)

		assertResponseBody(t, response.Body.String(), "20")
	})

	t.Run("returns Floyd's score", func(t *testing.T) {
		request := newGetScoreRequest("Floyd")
		response := httptest.NewRecorder()

		PlayerServer(response, request)

		assertResponseBody(t, response.Body.String(), "10")
	})
}

func newGetScoreRequest(name string) *http.Request {
	req, _ := http.NewRequest(http.MethodGet, fmt.Sprintf("/players/%s", name), nil)
	return req
}

func assertResponseBody(t testing.TB, got, want string) {
	t.Helper()
	if got != want {
		t.Errorf("response body is wrong, got %q want %q", got, want)
	}
}
```

Однако мы все еще не должны быть довольны. Кажется неправильным, что наш сервер знает счеты.

Наш рефакторинг ясно показал, что делать.

Мы переместили расчет счета из основной части нашего обработчика в функцию `GetPlayerScore`. Это кажется правильным местом для разделения обязанностей с использованием интерфейсов.

Давайте преобразуем нашу рефакторинговую функцию в интерфейс:

```go
type PlayerStore interface {
	GetPlayerScore(name string) int
}
```

Чтобы наш `PlayerServer` мог использовать `PlayerStore`, ему потребуется ссылка на него. Сейчас кажется подходящее время изменить нашу архитектуру так, чтобы наш `PlayerServer` теперь был `структурой`.

```go
type PlayerServer struct {
	store PlayerStore
}
```

Наконец, мы теперь реализуем интерфейс `Handler`, добавив метод к нашей новой структуре и поместив в него наш существующий код обработчика.

```go
func (p *PlayerServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	player := strings.TrimPrefix(r.URL.Path, "/players/")
	fmt.Fprint(w, p.store.GetPlayerScore(player))
}
```

Единственное другое изменение заключается в том, что теперь мы вызываем наш `store.GetPlayerScore` для получения счета, а не локальную функцию, которую мы определили (которую теперь можем удалить).

Вот полный листинг кода нашего сервера:

```go
//server.go
type PlayerStore interface {
	GetPlayerScore(name string) int
}

type PlayerServer struct {
	store PlayerStore
}

func (p *PlayerServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	player := strings.TrimPrefix(r.URL.Path, "/players/")
	fmt.Fprint(w, p.store.GetPlayerScore(player))
}
```

### Исправьте проблемы

Это было довольно много изменений, и мы знаем, что наши тесты и приложение больше не будут компилироваться, но просто расслабьтесь и дайте компилятору поработать.

`./main.go:9:58: type PlayerServer is not an expression`

Нам нужно изменить наши тесты, чтобы вместо этого создать новый экземпляр `PlayerServer`, а затем вызвать его метод `ServeHTTP`.

```go
//server_test.go
func TestGETPlayers(t *testing.T) {
	server := &PlayerServer{}

	t.Run("returns Pepper's score", func(t *testing.T) {
		request := newGetScoreRequest("Pepper")
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		assertResponseBody(t, response.Body.String(), "20")
	})

	t.Run("returns Floyd's score", func(t *testing.T) {
		request := newGetScoreRequest("Floyd")
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		assertResponseBody(t, response.Body.String(), "10")
	})
}
```

Обратите внимание, что мы все еще не беспокоимся о создании хранилищ *пока что*, мы просто хотим, чтобы компилятор проходил как можно скорее.

Вы должны привыкнуть к тому, чтобы приоритет отдавался компилируемому коду, а затем коду, проходящему тесты.

Добавляя больше функциональности (например, заглушки хранилищ) в то время, как код не компилируется, мы подвергаем себя потенциально *большему* количеству проблем с компиляцией.

Теперь `main.go` не будет компилироваться по той же причине.

```go
func main() {
	server := &PlayerServer{}
	log.Fatal(http.ListenAndServe(":5000", server))
}
```

Наконец, все компилируется, но тесты не проходят.

```
=== RUN   TestGETPlayers/returns_the_Pepper's_score
panic: runtime error: invalid memory address or nil pointer dereference [recovered]
    panic: runtime error: invalid memory address or nil pointer dereference
```

Это происходит потому, что мы не передали `PlayerStore` в наших тестах. Нам нужно будет создать его заглушку.

```go
//server_test.go
type StubPlayerStore struct {
	scores map[string]int
}

func (s *StubPlayerStore) GetPlayerScore(name string) int {
	score := s.scores[name]
	return score
}
```

`map` — это быстрый и простой способ создания заглушки хранилища ключ/значение для наших тестов. Теперь давайте создадим одно из этих хранилищ для наших тестов и отправим его в наш `PlayerServer`.

```go
//server_test.go
func TestGETPlayers(t *testing.T) {
	store := StubPlayerStore{
		map[string]int{
			"Pepper": 20,
			"Floyd":  10,
		},
	}
	server := &PlayerServer{&store}

	t.Run("returns Pepper's score", func(t *testing.T) {
		request := newGetScoreRequest("Pepper")
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		assertResponseBody(t, response.Body.String(), "20")
	})

	t.Run("returns Floyd's score", func(t *testing.T) {
		request := newGetScoreRequest("Floyd")
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		assertResponseBody(t, response.Body.String(), "10")
	})
}
```

Наши тесты теперь проходят и выглядят лучше. *Намерение* нашего кода стало яснее благодаря введению хранилища. Мы говорим читателю, что поскольку у нас есть *эти данные в `PlayerStore`*, при их использовании с `PlayerServer` вы должны получить следующие ответы.

### Запустите приложение

Теперь, когда наши тесты проходят, последнее, что нам нужно сделать, чтобы завершить этот рефакторинг, это проверить, работает ли наше приложение. Программа должна запуститься, но вы получите ужасный ответ, если попытаетесь обратиться к серверу по адресу `http://localhost:5000/players/Pepper`.

Причина этого в том, что мы не передали `PlayerStore`.

Нам нужно будет реализовать его, но сейчас это сложно, так как мы не храним никаких значимых данных, поэтому пока придется использовать жестко заданные значения.

```go
//main.go
type InMemoryPlayerStore struct{}

func (i *InMemoryPlayerStore) GetPlayerScore(name string) int {
	return 123
}

func main() {
	server := &PlayerServer{&InMemoryPlayerStore{}}
	log.Fatal(http.ListenAndServe(":5000", server))
}
```

Если вы снова запустите `go build` и обратитесь к тому же URL, вы должны получить `"123"`. Не очень хорошо, но пока мы не сохраним данные, это лучшее, что мы можем сделать.
Также не очень приятно, что наше основное приложение запускалось, но на самом деле не работало. Нам пришлось вручную тестировать, чтобы увидеть проблему.

У нас есть несколько вариантов, что делать дальше:

-   Обработать сценарий, когда игрок не существует.
-   Обработать сценарий `POST /players/{name}`.

Хотя сценарий `POST` приближает нас к "счастливому пути", я чувствую, что будет легче сначала разобраться со сценарием отсутствующего игрока, так как мы уже находимся в этом контексте. До остального мы доберемся позже.

## Сначала напишите тест

Добавьте сценарий с отсутствующим игроком в наш существующий набор тестов.

```go
//server_test.go
t.Run("returns 404 on missing players", func(t *testing.T) {
	request := newGetScoreRequest("Apollo")
	response := httptest.NewRecorder()

	server.ServeHTTP(response, request)

	got := response.Code
	want := http.StatusNotFound

	if got != want {
		t.Errorf("got status %d want %d", got, want)
	}
})
```

## Попытайтесь запустить тест

```
=== RUN   TestGETPlayers/returns_404_on_missing_players
    --- FAIL: TestGETPlayers/returns_404_on_missing_players (0.00s)
        server_test.go:56: got status 200 want 404
```

## Напишите достаточно кода, чтобы он прошел

Иногда я закатываю глаза, когда сторонники TDD говорят "убедитесь, что вы пишете минимальное количество кода, чтобы он прошел", так как это может показаться очень педантичным.

Но этот сценарий хорошо иллюстрирует пример. Я сделал минимум (зная, что это неверно), а именно написал `StatusNotFound` для **всех ответов**, но все наши тесты проходят!

**Выполняя минимум действий для прохождения тестов, можно выявить пробелы в ваших тестах**. В нашем случае мы не утверждаем, что должны получать `StatusOK`, когда игроки *существуют* в хранилище.

Обновите два других теста, чтобы проверить статус, и исправьте код.

Вот новые тесты:

```go
//server_test.go
func TestGETPlayers(t *testing.T) {
	store := StubPlayerStore{
		map[string]int{
			"Pepper": 20,
			"Floyd":  10,
		},
	}
	server := &PlayerServer{&store}

	t.Run("returns Pepper's score", func(t *testing.T) {
		request := newGetScoreRequest("Pepper")
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		assertStatus(t, response.Code, http.StatusOK)
		assertResponseBody(t, response.Body.String(), "20")
	})

	t.Run("returns Floyd's score", func(t *testing.T) {
		request := newGetScoreRequest("Floyd")
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		assertStatus(t, response.Code, http.StatusOK)
		assertResponseBody(t, response.Body.String(), "10")
	})

	t.Run("returns 404 on missing players", func(t *testing.T) {
		request := newGetScoreRequest("Apollo")
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		assertStatus(t, response.Code, http.StatusNotFound)
	})
}

func assertStatus(t testing.TB, got, want int) {
	t.Helper()
	if got != want {
		t.Errorf("did not get correct status, got %d, want %d", got, want)
	}
}

func newGetScoreRequest(name string) *http.Request {
	req, _ := http.NewRequest(http.MethodGet, fmt.Sprintf("/players/%s", name), nil)
	return req
}

func assertResponseBody(t testing.TB, got, want string) {
	t.Helper()
	if got != want {
		t.Errorf("response body is wrong, got %q want %q", got, want)
	}
}
```

Теперь мы проверяем статус во всех наших тестах, поэтому я сделал вспомогательную функцию `assertStatus`, чтобы облегчить это.

Теперь наши первые два теста падают из-за 404 вместо 200, поэтому мы можем исправить `PlayerServer`, чтобы он возвращал "не найдено" только в том случае, если счет равен 0.

```go
//server.go
func (p *PlayerServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	player := strings.TrimPrefix(r.URL.Path, "/players/")

	score := p.store.GetPlayerScore(player)

	if score == 0 {
		w.WriteHeader(http.StatusNotFound)
	}

	fmt.Fprint(w, score)
}
```

### Хранение результатов

Теперь, когда мы можем получать результаты из хранилища, имеет смысл иметь возможность сохранять новые результаты.

## Сначала напишите тест

```go
//server_test.go
func TestStoreWins(t *testing.T) {
	store := StubPlayerStore{
		map[string]int{},
	}
	server := &PlayerServer{&store}

	t.Run("it returns accepted on POST", func(t *testing.T) {
		request, _ := http.NewRequest(http.MethodPost, "/players/Pepper", nil)
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		assertStatus(t, response.Code, http.StatusAccepted)
	})
}
```

Для начала давайте просто проверим, что мы получаем правильный код статуса, если обращаемся к определенному маршруту с помощью POST. Это позволит нам развить функциональность принятия другого типа запроса и его обработки, отличной от `GET /players/{name}`. Как только это заработает, мы сможем начать проверять взаимодействие нашего обработчика с хранилищем.

## Попытайтесь запустить тест

```
=== RUN   TestStoreWins/it_returns_accepted_on_POST
    --- FAIL: TestStoreWins/it_returns_accepted_on_POST (0.00s)
        server_test.go:70: did not get correct status, got 404, want 202
```

## Напишите достаточно кода, чтобы он прошел

Помните, что мы намеренно совершаем ошибки, поэтому условный оператор `if` на основе метода запроса сработает.

```go
//server.go
func (p *PlayerServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {

	if r.Method == http.MethodPost {
		w.WriteHeader(http.StatusAccepted)
		return
	}

	player := strings.TrimPrefix(r.URL.Path, "/players/")

	score := p.store.GetPlayerScore(player)

	if score == 0 {
		w.WriteHeader(http.StatusNotFound)
	}

	fmt.Fprint(w, score)
}
```

## Рефакторинг

Обработчик сейчас выглядит немного запутанным. Давайте разобьем код, чтобы его было легче понять и выделить различную функциональность в новые функции.

```go
//server.go
func (p *PlayerServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {

	switch r.Method {
	case http.MethodPost:
		p.processWin(w)
	case http.MethodGet:
		p.showScore(w, r)
	}

}

func (p *PlayerServer) showScore(w http.ResponseWriter, r *http.Request) {
	player := strings.TrimPrefix(r.URL.Path, "/players/")

	score := p.store.GetPlayerScore(player)

	if score == 0 {
		w.WriteHeader(http.StatusNotFound)
	}

	fmt.Fprint(w, score)
}

func (p *PlayerServer) processWin(w http.ResponseWriter) {
	w.WriteHeader(http.StatusAccepted)
}
```

Это делает аспект маршрутизации `ServeHTTP` немного более понятным и означает, что наши следующие итерации по хранению данных могут быть просто внутри `processWin`.

Далее мы хотим проверить, что когда мы выполняем `POST /players/{name}`, нашему `PlayerStore` сообщается о необходимости записи победы.

## Сначала напишите тест

Мы можем добиться этого, расширив наш `StubPlayerStore` новым методом `RecordWin` и затем отслеживая его вызовы.

```go
//server_test.go
type StubPlayerStore struct {
	scores   map[string]int
	winCalls []string
}

func (s *StubPlayerStore) GetPlayerScore(name string) int {
	score := s.scores[name]
	return score
}

func (s *StubPlayerStore) RecordWin(name string) {
	s.winCalls = append(s.winCalls, name)
}
```

Теперь расширим наш тест, чтобы для начала проверить количество вызовов.

```go
//server_test.go
func TestStoreWins(t *testing.T) {
	store := StubPlayerStore{
		map[string]int{},
	}
	server := &PlayerServer{&store}

	t.Run("it records wins when POST", func(t *testing.T) {
		request := newPostWinRequest("Pepper")
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		assertStatus(t, response.Code, http.StatusAccepted)

		if len(store.winCalls) != 1 {
			t.Errorf("got %d calls to RecordWin want %d", len(store.winCalls), 1)
		}
	})
}

func newPostWinRequest(name string) *http.Request {
	req, _ := http.NewRequest(http.MethodPost, fmt.Sprintf("/players/%s", name), nil)
	return req
}
```

## Попытайтесь запустить тест

```
./server_test.go:26:20: too few values in struct initializer
./server_test.go:65:20: too few values in struct initializer
```

## Напишите минимальное количество кода, чтобы тест запустился и проверьте вывод неудачного теста

Нам нужно обновить наш код, где мы создаем `StubPlayerStore`, так как мы добавили новое поле.

```go
//server_test.go
store := StubPlayerStore{
	map[string]int{},
	nil,
}
```

```
--- FAIL: TestStoreWins (0.00s)
    --- FAIL: TestStoreWins/it_records_wins_when_POST (0.00s)
        server_test.go:80: got 0 calls to RecordWin want 1
```

## Напишите достаточно кода, чтобы он прошел

Поскольку мы проверяем только количество вызовов, а не конкретные значения, наша начальная итерация становится немного меньше.

Нам нужно обновить представление `PlayerServer` о том, что такое `PlayerStore`, изменив интерфейс, если мы собираемся вызывать `RecordWin`.

```go
//server.go
type PlayerStore interface {
	GetPlayerScore(name string) int
	RecordWin(name string)
}
```

Из-за этого `main` больше не компилируется.

```
./main.go:17:46: cannot use InMemoryPlayerStore literal (type *InMemoryPlayerStore) as type PlayerStore in field value:
    *InMemoryPlayerStore does not implement PlayerStore (missing RecordWin method)
```

Компилятор говорит нам, что не так. Давайте обновим `InMemoryPlayerStore`, чтобы у него был этот метод.

```go
//main.go
type InMemoryPlayerStore struct{}

func (i *InMemoryPlayerStore) RecordWin(name string) {}
```

Попробуйте запустить тесты, и мы должны вернуться к компилируемому коду — но тест все еще падает.

Теперь, когда `PlayerStore` имеет `RecordWin`, мы можем вызвать его в нашем `PlayerServer`.

```go
//server.go
func (p *PlayerServer) processWin(w http.ResponseWriter) {
	p.store.RecordWin("Bob")
	w.WriteHeader(http.StatusAccepted)
}
```

Запустите тесты, и они должны пройти! Очевидно, `"Bob"` — это не совсем то, что мы хотим отправить в `RecordWin`, поэтому давайте доработаем тест.

## Сначала напишите тест

```go
//server_test.go
func TestStoreWins(t *testing.T) {
	store := StubPlayerStore{
		map[string]int{},
		nil,
	}
	server := &PlayerServer{&store}

	t.Run("it records wins on POST", func(t *testing.T) {
		player := "Pepper"

		request := newPostWinRequest(player)
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		assertStatus(t, response.Code, http.StatusAccepted)

		if len(store.winCalls) != 1 {
			t.Fatalf("got %d calls to RecordWin want %d", len(store.winCalls), 1)
		}

		if store.winCalls[0] != player {
			t.Errorf("did not store correct winner got %q want %q", store.winCalls[0], player)
		}
	})
}
```

Теперь, когда мы знаем, что в нашем срезе `winCalls` есть один элемент, мы можем безопасно обратиться к первому элементу и проверить, равен ли он `player`.

## Попытайтесь запустить тест

```
=== RUN   TestStoreWins/it_records_wins_on_POST
    --- FAIL: TestStoreWins/it_records_wins_on_POST (0.00s)
        server_test.go:86: did not store correct winner got 'Bob' want 'Pepper'
```

## Напишите достаточно кода, чтобы он прошел

```go
//server.go
func (p *PlayerServer) processWin(w http.ResponseWriter, r *http.Request) {
	player := strings.TrimPrefix(r.URL.Path, "/players/")
	p.store.RecordWin(player)
	w.WriteHeader(http.StatusAccepted)
}
```

Мы изменили `processWin`, чтобы он принимал `http.Request`, чтобы мы могли посмотреть на URL и извлечь имя игрока. Как только у нас это будет, мы можем вызвать наше `store` с правильным значением, чтобы тест прошел.

## Рефакторинг

Мы можем немного упростить этот код, поскольку мы извлекаем имя игрока одним и тем же способом в двух местах.

```go
//server.go
func (p *PlayerServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	player := strings.TrimPrefix(r.URL.Path, "/players/")

	switch r.Method {
	case http.MethodPost:
		p.processWin(w, player)
	case http.MethodGet:
		p.showScore(w, player)
	}
}

func (p *PlayerServer) showScore(w http.ResponseWriter, player string) {
	score := p.store.GetPlayerScore(player)

	if score == 0 {
		w.WriteHeader(http.StatusNotFound)
	}

	fmt.Fprint(w, score)
}

func (p *PlayerServer) processWin(w http.ResponseWriter, player string) {
	p.store.RecordWin(player)
	w.WriteHeader(http.StatusAccepted)
}
```

Хотя наши тесты проходят, у нас на самом деле нет работающего программного обеспечения. Если вы попытаетесь запустить `main` и использовать программу по назначению, она не будет работать, потому что мы еще не реализовали `PlayerStore` должным образом. Однако это нормально; сосредоточившись на нашем обработчике, мы определили интерфейс, который нам нужен, вместо того, чтобы пытаться спроектировать его заранее.

Мы *могли бы* начать писать тесты для нашего `InMemoryPlayerStore`, но он здесь временно, пока мы не реализуем более надежный способ сохранения результатов игроков (например, базу данных).

Что мы сделаем сейчас, так это напишем *интеграционный тест* между нашим `PlayerServer` и `InMemoryPlayerStore`, чтобы завершить функциональность. Это позволит нам достичь нашей цели — быть уверенными в работе нашего приложения, не тестируя напрямую `InMemoryPlayerStore`. Более того, когда мы приступим к реализации `PlayerStore` с базой данных, мы сможем протестировать эту реализацию тем же интеграционным тестом.

### Интеграционные тесты

Интеграционные тесты могут быть полезны для проверки работы больших областей вашей системы, но вы должны иметь в виду:

-   Их сложнее писать.
-   Когда они падают, может быть трудно понять, почему (обычно это ошибка в компоненте интеграционного теста), и, следовательно, их сложнее исправлять.
-   Они иногда медленнее выполняются (так как часто используются с "реальными" компонентами, такими как база данных).

По этой причине рекомендуется изучить *пирамиду тестирования*.

## Сначала напишите тест

В интересах краткости я покажу вам окончательный рефакторинговый интеграционный тест.

```go
// server_integration_test.go
package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestRecordingWinsAndRetrievingThem(t *testing.T) {
	store := InMemoryPlayerStore{}
	server := PlayerServer{&store}
	player := "Pepper"

	server.ServeHTTP(httptest.NewRecorder(), newPostWinRequest(player))
	server.ServeHTTP(httptest.NewRecorder(), newPostWinRequest(player))
	server.ServeHTTP(httptest.NewRecorder(), newPostWinRequest(player))

	response := httptest.NewRecorder()
	server.ServeHTTP(response, newGetScoreRequest(player))
	assertStatus(t, response.Code, http.StatusOK)

	assertResponseBody(t, response.Body.String(), "3")
}
```

-   Мы создаем два компонента, которые пытаемся интегрировать: `InMemoryPlayerStore` и `PlayerServer`.
-   Затем мы отправляем 3 запроса для записи 3 побед для `player`. Мы не слишком обеспокоены кодами статуса в этом тесте, так как это не имеет отношения к тому, насколько хорошо они интегрируются.
-   Следующий ответ, который нас интересует (поэтому мы сохраняем переменную `response`), потому что мы собираемся попытаться получить счет `player`.

## Попытайтесь запустить тест

```
--- FAIL: TestRecordingWinsAndRetrievingThem (0.00s)
    server_integration_test.go:24: response body is wrong, got '123' want '3'
```

## Напишите достаточно кода, чтобы он прошел

Я позволю себе здесь некоторую вольность и напишу больше кода, чем вы, возможно, привыкли, без написания теста.

*Это разрешено!* У нас все еще есть тест, проверяющий, что все должно работать правильно, но он не касается конкретного модуля, с которым мы работаем (`InMemoryPlayerStore`).

Если бы я застрял в этом сценарии, я бы отменил свои изменения до падающего теста, а затем написал бы более конкретные модульные тесты для `InMemoryPlayerStore`, чтобы помочь мне найти решение.

```go
//in_memory_player_store.go
func NewInMemoryPlayerStore() *InMemoryPlayerStore {
	return &InMemoryPlayerStore{map[string]int{}}
}

type InMemoryPlayerStore struct {
	store map[string]int
}

func (i *InMemoryPlayerStore) RecordWin(name string) {
	i.store[name]++
}

func (i *InMemoryPlayerStore) GetPlayerScore(name string) int {
	return i.store[name]
}
```

-   Нам нужно хранить данные, поэтому я добавил `map[string]int` в структуру `InMemoryPlayerStore`.
-   Для удобства я создал `NewInMemoryPlayerStore` для инициализации хранилища и обновил интеграционный тест, чтобы использовать его:
    ```go
    //server_integration_test.go
    store := NewInMemoryPlayerStore()
    server := PlayerServer{store}
    ```
-   Остальной код — это просто обертка вокруг `map`.

Интеграционный тест проходит, теперь нам просто нужно изменить `main` для использования `NewInMemoryPlayerStore()`.

```go
// main.go
package main

import (
	"log"
	"net/http"
)

func main() {
	server := &PlayerServer{NewInMemoryPlayerStore()}
	log.Fatal(http.ListenAndServe(":5000", server))
}
```

Соберите, запустите и затем используйте `curl` для проверки.

-   Запустите это несколько раз, измените имена игроков, если хотите: `curl -X POST http://localhost:5000/players/Pepper`
-   Проверьте результаты с помощью `curl http://localhost:5000/players/Pepper`

Отлично! Вы создали REST-подобный сервис. Чтобы двигаться дальше, вам нужно будет выбрать хранилище данных для сохранения результатов на более длительный срок, чем время работы программы.

-   Выберите хранилище (Bolt? Mongo? Postgres? Файловая система?)
-   Заставьте `PostgresPlayerStore` реализовать `PlayerStore`.
-   Протестируйте функциональность с помощью TDD, чтобы убедиться, что она работает.
-   Подключите его к интеграционному тесту, проверьте, все ли в порядке.
-   Наконец, подключите его к `main`.

## Рефакторинг

Мы почти у цели! Давайте приложим некоторые усилия для предотвращения ошибок параллелизма, подобных этим:

```
fatal error: concurrent map read and map write
```

Добавляя мьютексы, мы обеспечиваем безопасность параллелизма, особенно для счетчика в нашей функции `RecordWin`. Подробнее о мьютексах читайте в главе о пакете `sync`.

## Завершение

### `http.Handler`

-   Реализуйте этот интерфейс для создания веб-серверов.
-   Используйте `http.HandlerFunc` для превращения обычных функций в `http.Handler`ы.
-   Используйте `httptest.NewRecorder` в качестве `ResponseWriter`, чтобы можно было отслеживать ответы, отправляемые вашим обработчиком.
-   Используйте `http.NewRequest` для конструирования запросов, которые, как вы ожидаете, поступят в вашу систему.

### Интерфейсы, мокирование и внедрение зависимостей (DI)

-   Позволяет итеративно строить систему по частям.
-   Позволяет разрабатывать обработчик, которому требуется хранилище, без необходимости использования фактического хранилища.
-   TDD для создания необходимых интерфейсов.

### Совершайте ошибки, затем рефакторинг (а затем фиксируйте в системе контроля версий)

-   Вы должны рассматривать сбой компиляции или падающие тесты как "красную" ситуацию, из которой нужно выбраться как можно скорее.
-   Напишите только необходимый код, чтобы достичь этого. *Затем* проведите рефакторинг и сделайте код красивым.
-   Попытка внести слишком много изменений, пока код не компилируется или тесты падают, подвергает вас риску усугубления проблем.
-   Придерживаясь этого подхода, вы вынуждены писать небольшие тесты, что означает небольшие изменения, что помогает поддерживать работу над сложными системами управляемой.