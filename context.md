# Контекст

**[Весь код для этой главы вы найдете здесь](https://github.com/quii/learn-go-with-tests/tree/main/context)**

Программное обеспечение часто запускает длительные, ресурсоемкие процессы (часто в горутинах). Если действие, вызвавшее это, отменяется или терпит неудачу по какой-либо причине, вам необходимо остановить эти процессы согласованным образом во всем приложении.

Если вы не будете управлять этим, ваше быстрое Go-приложение, которым вы так гордитесь, может начать сталкиваться с труднодиагностируемыми проблемами производительности.

В этой главе мы будем использовать пакет `context`, чтобы помочь нам управлять длительными процессами.

Мы начнем с классического примера веб-сервера, который при обращении к нему запускает потенциально длительный процесс получения данных, чтобы вернуть их в ответе.

Мы рассмотрим сценарий, когда пользователь отменяет запрос до того, как данные могут быть получены, и убедимся, что процессу указано прекратить работу.

Я настроил некоторый код для "счастливого пути" (happy path), чтобы мы могли начать. Вот наш код сервера.

```go
func Server(store Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, store.Fetch())
	}
}
```

Функция `Server` принимает `Store` и возвращает нам `http.HandlerFunc`. `Store` определяется как:

```go
type Store interface {
	Fetch() string
}
```

Возвращенная функция вызывает метод `Fetch` `store`, чтобы получить данные и записывает их в ответ.

У нас есть соответствующий шпион (spy) для `Store`, который мы используем в тесте.

```go
type SpyStore struct {
	response string
}

func (s *SpyStore) Fetch() string {
	return s.response
}

func TestServer(t *testing.T) {
	data := "hello, world"
	svr := Server(&SpyStore{data})

	request := httptest.NewRequest(http.MethodGet, "/", nil)
	response := httptest.NewRecorder()

	svr.ServeHTTP(response, request)

	if response.Body.String() != data {
		t.Errorf(`got "%s", want "%s"`, response.Body.String(), data)
	}
}
```

Теперь, когда у нас есть "счастливый путь", мы хотим создать более реалистичный сценарий, в котором `Store` не может завершить `Fetch` до того, как пользователь отменит запрос.

## Сначала напишите тест

Нашему обработчику понадобится способ сообщить `Store` об отмене работы, поэтому обновим интерфейс.

```go
type Store interface {
	Fetch() string
	Cancel()
}
```

Нам нужно будет настроить наш шпион так, чтобы он занимал некоторое время для возврата `data` и имел способ узнать, что ему было приказано отменить. Ему придется добавить `Cancel` в качестве метода для реализации интерфейса `Store`.

```go
type SpyStore struct {
	response  string
	cancelled bool
}

func (s *SpyStore) Fetch() string {
	time.Sleep(100 * time.Millisecond)
	return s.response
}

func (s *SpyStore) Cancel() {
	s.cancelled = true
}
```

Добавим новый тест, в котором мы отменяем запрос до истечения 100 миллисекунд и проверяем хранилище, чтобы увидеть, отменяется ли оно.

```go
t.Run("tells store to cancel work if request is cancelled", func(t *testing.T) {
	data := "hello, world"
	store := &SpyStore{response: data}
	svr := Server(store)

	request := httptest.NewRequest(http.MethodGet, "/", nil)

	cancellingCtx, cancel := context.WithCancel(request.Context())
	time.AfterFunc(5*time.Millisecond, cancel)
	request = request.WithContext(cancellingCtx)

	response := httptest.NewRecorder()

	svr.ServeHTTP(response, request)

	if !store.cancelled {
		t.Error("store was not told to cancel")
	}
})
```

Из [блога Go: Context](https://blog.golang.org/context)

> Пакет context предоставляет функции для получения новых значений Context из существующих. Эти значения образуют дерево: когда Context отменяется, все Contexts, полученные из него, также отменяются.

Важно, чтобы вы получали свои контексты таким образом, чтобы отмены распространялись по всему стеку вызовов для данного запроса.

Что мы делаем, так это получаем новый `cancellingCtx` из нашего `request`, который возвращает нам функцию `cancel`. Затем мы планируем вызов этой функции через 5 миллисекунд, используя `time.AfterFunc`. Наконец, мы используем этот новый контекст в нашем запросе, вызывая `request.WithContext`.

## Попробуйте запустить тест

Тест завершается неудачей, как мы и ожидали.

```
--- FAIL: TestServer (0.00s)
    --- FAIL: TestServer/tells_store_to_cancel_work_if_request_is_cancelled (0.00s)
    	context_test.go:62: store was not told to cancel
```

## Напишите достаточно кода, чтобы тест прошел

Помните о дисциплине при работе с TDD. Напишите _минимальное_ количество кода, чтобы наш тест прошел.

```go
func Server(store Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		store.Cancel()
		fmt.Fprint(w, store.Fetch())
	}
}
```

Это заставляет тест пройти, но это не очень хорошо, не так ли! Мы, конечно, не должны вызывать `Cancel()` до того, как мы получим данные при _каждом запросе_.

Благодаря дисциплине это выявило недостаток в наших тестах, и это хорошо!

Нам нужно будет обновить наш тест "счастливого пути", чтобы убедиться, что отмена не происходит.

```go
t.Run("returns data from store", func(t *testing.T) {
	data := "hello, world"
	store := &SpyStore{response: data}
	svr := Server(store)

	request := httptest.NewRequest(http.MethodGet, "/", nil)
	response := httptest.NewRecorder()

	svr.ServeHTTP(response, request)

	if response.Body.String() != data {
		t.Errorf(`got "%s", want "%s"`, response.Body.String(), data)
	}

	if store.cancelled {
		t.Error("it should not have cancelled the store")
	}
})
```

Запустите оба теста, и тест "счастливого пути" теперь должен завершаться неудачей, и теперь мы вынуждены реализовать более разумный подход.

```go
func Server(store Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ctx := r.Context()

		data := make(chan string, 1)

		go func() {
			data <- store.Fetch()
		}()

		select {
		case d := <-data:
			fmt.Fprint(w, d)
		case <-ctx.Done():
			store.Cancel()
		}
	}
}
```

Что мы здесь сделали?

Пакет `context` имеет метод `Done()`, который возвращает канал, в который отправляется сигнал, когда контекст "завершен" или "отменен". Мы хотим прослушивать этот сигнал и вызывать `store.Cancel`, если получаем его, но хотим игнорировать его, если наш `Store` успевает выполнить `Fetch` до этого.

Чтобы управлять этим, мы запускаем `Fetch` в горутине, и она записывает результат в новый канал `data`. Затем мы используем `select` для эффективного соревнования двух асинхронных процессов, и затем мы либо записываем ответ, либо вызываем `Cancel`.

## Рефакторинг

Мы можем немного рефакторить наш тестовый код, создав методы утверждения в нашем шпионе.

```go
type SpyStore struct {
	response  string
	cancelled bool
	t         *testing.T
}

func (s *SpyStore) assertWasCancelled() {
	s.t.Helper()
	if !s.cancelled {
		s.t.Error("store was not told to cancel")
	}
}

func (s *SpyStore) assertWasNotCancelled() {
	s.t.Helper()
	if s.cancelled {
		s.t.Error("store was told to cancel")
	}
}
```

Не забудьте передать `*testing.T` при создании шпиона.

```go
func TestServer(t *testing.T) {
	data := "hello, world"

	t.Run("returns data from store", func(t *testing.T) {
		store := &SpyStore{response: data, t: t}
		svr := Server(store)

		request := httptest.NewRequest(http.MethodGet, "/", nil)
		response := httptest.NewRecorder()

		svr.ServeHTTP(response, request)

		if response.Body.String() != data {
			t.Errorf(`got "%s", want "%s"`, response.Body.String(), data)
		}

		store.assertWasNotCancelled()
	})

	t.Run("tells store to cancel work if request is cancelled", func(t *testing.T) {
		store := &SpyStore{response: data, t: t}
		svr := Server(store)

		request := httptest.NewRequest(http.MethodGet, "/", nil)

		cancellingCtx, cancel := context.WithCancel(request.Context())
		time.AfterFunc(5*time.Millisecond, cancel)
		request = request.WithContext(cancellingCtx)

		response := httptest.NewRecorder()

		svr.ServeHTTP(response, request)

		store.assertWasCancelled()
	})
}
```

Этот подход приемлем, но является ли он идиоматичным?

Разумно ли, чтобы наш веб-сервер занимался ручной отменой `Store`? Что если `Store` также зависит от других медленно работающих процессов? Нам придется убедиться, что `Store.Cancel` правильно распространяет отмену на всех своих зависимых объектов.

Одна из основных целей `context` заключается в том, что он предоставляет последовательный способ отмены.

[Из документации Go](https://golang.org/pkg/context/)

> Входящие запросы к серверу должны создавать Context, а исходящие вызовы к серверам должны принимать Context. Цепочка вызовов функций между ними должна распространять Context, опционально заменяя его на производный Context, созданный с помощью WithCancel, WithDeadline, WithTimeout или WithValue. Когда Context отменяется, все Contexts, полученные из него, также отменяются.

Снова из [блога Go: Context](https://blog.golang.org/context):

> В Google мы требуем, чтобы Go-программисты передавали параметр Context первым аргументом в каждую функцию на пути вызовов между входящими и исходящими запросами. Это позволяет Go-коду, разработанному многими различными командами, хорошо взаимодействовать. Это обеспечивает простое управление таймаутами и отменой, а также гарантирует, что критически важные значения, такие как учетные данные безопасности, правильно передаются по Go-программам.

(Остановитесь на мгновение и подумайте о последствиях того, что каждая функция должна передавать контекст, и об эргономике этого.)

Чувствуете себя немного неловко? Хорошо. Давайте попробуем следовать этому подходу и вместо этого передадим `context` в наш `Store`, чтобы он был ответственным. Таким образом, он также сможет передать `context` своим зависимым объектам, и они тоже смогут быть ответственными за свою остановку.

## Сначала напишите тест

Нам придется изменить наши существующие тесты, поскольку их обязанности меняются. Единственное, за что теперь отвечает наш обработчик, это убедиться, что он передает контекст нижестоящему `Store` и что он обрабатывает ошибку, которая придет из `Store` при его отмене.

Давайте обновим наш интерфейс `Store`, чтобы показать новые обязанности.

```go
type Store interface {
	Fetch(ctx context.Context) (string, error)
}
```

Пока удалим код внутри нашего обработчика.

```go
func Server(store Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
	}
}
```

Обновим наш `SpyStore`

```go
type SpyStore struct {
	response string
	t        *testing.T
}

func (s *SpyStore) Fetch(ctx context.Context) (string, error) {
	data := make(chan string, 1)

	go func() {
		var result string
		for _, c := range s.response {
			select {
			case <-ctx.Done():
				log.Println("spy store got cancelled")
				return
			default:
				time.Sleep(10 * time.Millisecond)
				result += string(c)
			}
		}
		data <- result
	}()

	select {
	case <-ctx.Done():
		return "", ctx.Err()
	case res := <-data:
		return res, nil
	}
}
```

Мы должны заставить наш шпион действовать как настоящий метод, который работает с `context`.

Мы симулируем медленный процесс, где мы медленно строим результат, добавляя строку, символ за символом, в горутине. Когда горутина завершает свою работу, она записывает строку в канал `data`. Горутина прослушивает `ctx.Done` и прекратит работу, если в этот канал будет отправлен сигнал.

Наконец, код использует другой `select`, чтобы дождаться завершения работы этой горутины или отмены.

Это похоже на наш предыдущий подход: мы используем примитивы параллелизма Go, чтобы заставить два асинхронных процесса соревноваться друг с другом, чтобы определить, что мы возвращаем.

Вы будете использовать аналогичный подход при написании собственных функций и методов, которые принимают `context`, поэтому убедитесь, что вы понимаете, что происходит.

Наконец, мы можем обновить наши тесты. Закомментируйте наш тест отмены, чтобы сначала исправить тест "счастливого пути".

```go
t.Run("returns data from store", func(t *testing.T) {
	data := "hello, world"
	store := &SpyStore{response: data, t: t}
	svr := Server(store)

	request := httptest.NewRequest(http.MethodGet, "/", nil)
	response := httptest.NewRecorder()

	svr.ServeHTTP(response, request)

	if response.Body.String() != data {
		t.Errorf(`got "%s", want "%s"`, response.Body.String(), data)
	}
})
```

## Попробуйте запустить тест

```
=== RUN   TestServer/returns_data_from_store
--- FAIL: TestServer (0.00s)
    --- FAIL: TestServer/returns_data_from_store (0.00s)
    	context_test.go:22: got "", want "hello, world"
```

## Напишите достаточно кода, чтобы тест прошел

```go
func Server(store Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		data, _ := store.Fetch(r.Context())
		fmt.Fprint(w, data)
	}
}
```

Наш "счастливый путь" должен быть... счастливым. Теперь мы можем исправить другой тест.

## Сначала напишите тест

Нам нужно проверить, что мы не записываем какой-либо ответ в случае ошибки. К сожалению, `httptest.ResponseRecorder` не имеет способа выяснить это, поэтому нам придется создать свой собственный шпион для этого.

```go
type SpyResponseWriter struct {
	written bool
}

func (s *SpyResponseWriter) Header() http.Header {
	s.written = true
	return nil
}

func (s *SpyResponseWriter) Write([]byte) (int, error) {
	s.written = true
	return 0, errors.New("not implemented")
}

func (s *SpyResponseWriter) WriteHeader(statusCode int) {
	s.written = true
}
```

Наш `SpyResponseWriter` реализует `http.ResponseWriter`, поэтому мы можем использовать его в тесте.

```go
t.Run("tells store to cancel work if request is cancelled", func(t *testing.T) {
	data := "hello, world"
	store := &SpyStore{response: data, t: t}
	svr := Server(store)

	request := httptest.NewRequest(http.MethodGet, "/", nil)

	cancellingCtx, cancel := context.WithCancel(request.Context())
	time.AfterFunc(5*time.Millisecond, cancel)
	request = request.WithContext(cancellingCtx)

	response := &SpyResponseWriter{}

	svr.ServeHTTP(response, request)

	if response.written {
		t.Error("a response should not have been written")
	}
})
```

## Попробуйте запустить тест

```
=== RUN   TestServer
=== RUN   TestServer/tells_store_to_cancel_work_if_request_is_cancelled
--- FAIL: TestServer (0.01s)
    --- FAIL: TestServer/tells_store_to_cancel_work_if_request_is_cancelled (0.01s)
    	context_test.go:47: a response should not have been written
```

## Напишите достаточно кода, чтобы тест прошел

```go
func Server(store Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		data, err := store.Fetch(r.Context())

		if err != nil {
			return // todo: log error however you like
		}

		fmt.Fprint(w, data)
	}
}
```

После этого мы видим, что код сервера упростился, поскольку он больше не несет явной ответственности за отмену; он просто передает `context` и полагается на нижестоящие функции, которые должны учитывать любые возможные отмены.

## Подведение итогов

### Что мы рассмотрели

- Как тестировать HTTP-обработчик, запрос которого был отменен клиентом.
- Как использовать context для управления отменой.
- Как написать функцию, которая принимает `context` и использует его для самоотмены с помощью горутин, `select` и каналов.
- Как следовать рекомендациям Google по управлению отменой, распространяя контекст, привязанный к запросу, по всему стеку вызовов.
- Как создать свой собственный шпион для `http.ResponseWriter`, если он вам нужен.

### Что насчет context.Value?

У [Михала Штрба](https://faiface.github.io/post/context-should-go-away-go2/) и у меня схожее мнение.

> Если вы используете ctx.Value в моей (несуществующей) компании, вы уволены

Некоторые инженеры выступали за передачу значений через `context`, поскольку это _кажется удобным_.

Удобство часто является причиной плохого кода.

Проблема с `context.Values` в том, что это просто нетипизированная карта, поэтому у вас нет типовой безопасности, и вам приходится обрабатывать случаи, когда она на самом деле не содержит вашего значения. Вы вынуждены создавать связь ключей карты между модулями, и если кто-то что-то меняет, всё начинает ломаться.

Короче говоря, **если функции нужны какие-то значения, передавайте их как типизированные параметры, а не пытайтесь получить их из `context.Value`**. Это делает их статически проверяемыми и задокументированными для всеобщего обозрения.

#### Но...

С другой стороны, может быть полезно включать информацию, ортогональную запросу, в контекст, например, идентификатор трассировки. Потенциально эта информация не понадобится каждой функции в вашем стеке вызовов и сделает ваши функциональные сигнатуры очень запутанными.

[Джек Линдамуд говорит: **Context.Value должно информировать, а не управлять**](https://medium.com/@cep21/how-to-correctly-use-context-context-in-go-1-7-8f2c0fafdf39)

> Содержимое context.Value предназначено для сопровождающих, а не для пользователей. Оно никогда не должно быть обязательным вводом для документированных или ожидаемых результатов.

### Дополнительные материалы

- Мне очень понравилось читать статью [Context should go away for Go 2 Михала Штрба](https://faiface.github.io/post/context-should-go-away-go2/). Его аргумент заключается в том, что необходимость передавать `context` повсюду — это "запах" кода, указывающий на недостаток в языке в отношении отмены. Он говорит, что было бы лучше, если бы это было как-то решено на уровне языка, а не на уровне библиотеки. Пока этого не произошло, вам понадобится `context`, если вы хотите управлять длительными процессами.
- В [блоге Go подробнее описывается мотивация для работы с `context` и приводятся некоторые примеры](https://blog.golang.org/context)