# Select

**[Весь код для этой главы вы найдете здесь](https://github.com/quii/learn-go-with-tests/tree/main/select)**

Вас попросили создать функцию `WebsiteRacer`, которая принимает два URL-адреса и "состязается" между ними, отправляя им HTTP GET-запросы и возвращая URL-адрес, который ответил первым. Если ни один из них не ответит в течение 10 секунд, функция должна вернуть `error`.

Для этого мы будем использовать:

-   пакет `net/http` для выполнения HTTP-вызовов.
-   пакет `net/http/httptest`, чтобы помочь нам их протестировать.
-   горутины.
-   `select` для синхронизации процессов.

## Сначала напишите тест

Начнем с чего-то наивного, чтобы начать работу.

```go
func TestRacer(t *testing.T) {
	slowURL := "http://www.facebook.com"
	fastURL := "http://www.quii.dev"

	want := fastURL
	got := Racer(slowURL, fastURL)

	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}
```

Мы знаем, что это не идеально и имеет проблемы, но это начало. Важно не слишком зацикливаться на том, чтобы все было идеально с первого раза.

## Попробуйте запустить тест

`./racer_test.go:14:9: undefined: Racer`

## Напишите минимальное количество кода, чтобы тест запустился, и проверьте вывод неудачного теста

```go
func Racer(a, b string) (winner string) {
	return
}
```

`racer_test.go:25: got '', want 'http://www.quii.dev'`

## Напишите достаточно кода, чтобы тест прошел

```go
func Racer(a, b string) (winner string) {
	startA := time.Now()
	http.Get(a)
	aDuration := time.Since(startA)

	startB := time.Now()
	http.Get(b)
	bDuration := time.Since(startB)

	if aDuration < bDuration {
		return a
	}

	return b
}
```

Для каждого URL-адреса:

1.  Мы используем `time.Now()`, чтобы записать время непосредственно перед попыткой получить `URL`.
2.  Затем мы используем [`http.Get`](https://golang.org/pkg/net/http/#Client.Get) для выполнения HTTP `GET`-запроса к `URL`. Эта функция возвращает [`http.Response`](https://golang.org/pkg/net/http/#Response) и `error`, но пока нас эти значения не интересуют.
3.  `time.Since` принимает начальное время и возвращает `time.Duration` — разницу между текущим и начальным временем.

Как только мы это сделали, мы просто сравниваем длительность, чтобы увидеть, что быстрее.

### Проблемы

Это может заставить тест пройти или не пройти для вас. Проблема в том, что мы обращаемся к реальным веб-сайтам для тестирования нашей собственной логики.

Тестирование кода, использующего HTTP, настолько распространено, что Go имеет инструменты в стандартной библиотеке, которые помогают в этом.

В главах, посвященных мокам и внедрению зависимостей, мы обсуждали, что в идеале мы не хотим полагаться на внешние сервисы для тестирования нашего кода, потому что они могут быть:

-   Медленными
-   Нестабильными
-   Не позволяют тестировать граничные случаи

В стандартной библиотеке есть пакет [`net/http/httptest`](https://golang.org/pkg/net/http/httptest/), который позволяет легко создавать мок-HTTP-сервер.

Давайте изменим наши тесты, чтобы использовать моки, и получим надежные серверы для тестирования, которыми мы можем управлять.

```go
func TestRacer(t *testing.T) {

	slowServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(20 * time.Millisecond)
		w.WriteHeader(http.StatusOK)
	}))

	fastServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	slowURL := slowServer.URL
	fastURL := fastServer.URL

	want := fastURL
	got := Racer(slowURL, fastURL)

	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}

	slowServer.Close()
	fastServer.Close()
}
```

Синтаксис может показаться немного сложным, но просто не торопитесь.

`httptest.NewServer` принимает `http.HandlerFunc`, который мы передаем через _анонимную функцию_.

`http.HandlerFunc` — это тип, который выглядит так: `type HandlerFunc func(ResponseWriter, *Request)`.

На самом деле он просто говорит, что ему нужна функция, которая принимает `ResponseWriter` и `Request`, что неудивительно для HTTP-сервера.

Оказывается, здесь нет никакой особой магии, **именно так вы бы написали _настоящий_ HTTP-сервер на Go**. Единственное отличие в том, что мы оборачиваем его в `httptest.NewServer`, что облегчает его использование при тестировании, поскольку он находит открытый порт для прослушивания, а затем вы можете закрыть его по окончании теста.

Внутри наших двух серверов мы заставляем медленный сервер коротко `time.Sleep` при получении запроса, чтобы сделать его медленнее, чем другой. Оба сервера затем записывают `OK`-ответ с `w.WriteHeader(http.StatusOK)` обратно вызывающей стороне.

Если вы перезапустите тест, он теперь определенно пройдет и должен быть быстрее. Поиграйте с этими задержками, чтобы намеренно сломать тест.

## Рефакторинг

У нас есть некоторая дубликация как в нашем производственном коде, так и в тестовом коде.

```go
func Racer(a, b string) (winner string) {
	aDuration := measureResponseTime(a)
	bDuration := measureResponseTime(b)

	if aDuration < bDuration {
		return a
	}

	return b
}

func measureResponseTime(url string) time.Duration {
	start := time.Now()
	http.Get(url)
	return time.Since(start)
}
```

Это устранение дублирования (`DRY-ing up`) делает наш код `Racer` намного более читаемым.

```go
func TestRacer(t *testing.T) {

	slowServer := makeDelayedServer(20 * time.Millisecond)
	fastServer := makeDelayedServer(0 * time.Millisecond)

	defer slowServer.Close()
	defer fastServer.Close()

	slowURL := slowServer.URL
	fastURL := fastServer.URL

	want := fastURL
	got := Racer(slowURL, fastURL)

	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func makeDelayedServer(delay time.Duration) *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(delay)
		w.WriteHeader(http.StatusOK)
	}))
}
```

Мы рефакторили создание наших фейковых серверов в функцию `makeDelayedServer`, чтобы переместить некоторый неинтересный код из теста и уменьшить повторение.

### `defer`

Префикс `defer` перед вызовом функции означает, что эта функция будет вызвана _в конце содержащей функции_.

Иногда вам нужно очищать ресурсы, например, закрывать файл или, в нашем случае, закрывать сервер, чтобы он не продолжал прослушивать порт.

Вы хотите, чтобы это выполнялось в конце функции, но при этом инструкция оставалась рядом с местом создания сервера для удобства будущих читателей кода.

Наш рефакторинг является улучшением и представляет собой разумное решение, учитывая рассмотренные функции Go, но мы можем сделать решение еще проще.

### Синхронизация процессов

-   Почему мы проверяем скорости веб-сайтов по очереди, когда Go отлично справляется с параллелизмом? Мы должны быть в состоянии проверять оба одновременно.
-   Нас на самом деле не интересует _точное время ответа_ на запросы, мы просто хотим знать, какой из них вернется первым.

Для этого мы введем новую конструкцию под названием `select`, которая помогает нам синхронизировать процессы очень легко и понятно.

```go
func Racer(a, b string) (winner string) {
	select {
	case <-ping(a):
		return a
	case <-ping(b):
		return b
	}
}

func ping(url string) chan struct{} {
	ch := make(chan struct{})
	go func() {
		http.Get(url)
		close(ch)
	}()
	return ch
}
```

#### `ping`

Мы определили функцию `ping`, которая создает `chan struct{}` и возвращает его.

В нашем случае нам не _важно_, какой тип отправляется в канал, _мы просто хотим сигнализировать, что мы закончили_, и закрытие канала работает отлично!

Почему `struct{}`, а не другой тип, например `bool`? Ну, `chan struct{}` — это наименьший из доступных типов данных с точки зрения памяти, поэтому мы не получаем выделения памяти в отличие от `bool`. Поскольку мы закрываем, а не отправляем что-либо в канал, зачем что-то выделять?

Внутри той же функции мы запускаем горутину, которая отправит сигнал в этот канал, как только мы завершим `http.Get(url)`.

##### Всегда `make` каналы

Обратите внимание, что мы должны использовать `make` при создании канала; а не, скажем, `var ch chan struct{}`. Когда вы используете `var`, переменная будет инициализирована "нулевым" значением своего типа. Например, для `string` это `""`, для `int` это 0 и т.д.

Для каналов нулевое значение — `nil`, и если вы попытаетесь отправить в него с помощью `<-`, он заблокируется навсегда, потому что вы не можете отправлять в `nil`-каналы.

[Вы можете увидеть это в действии в The Go Playground](https://play.golang.org/p/IIbeAox5jKA)
#### `select`

Вы помните из главы о параллелизме, что можно ждать значений, отправляемых в канал, с помощью `myVar := <-ch`. Это _блокирующий_ вызов, так как вы ждете значения.

`select` позволяет вам ждать _нескольких_ каналов. Первый, кто отправит значение, "выигрывает", и код под `case` выполняется.

Мы используем `ping` в нашем `select` для создания двух каналов, по одному для каждого из наших `URL`. Тот, кто первым запишет что-то в свой канал, выполнит свой код в `select`, что приведет к возврату его `URL` (и он станет победителем).

После этих изменений, смысл нашего кода очень ясен, а реализация на самом деле проще.

### Таймауты

Нашим последним требованием было возвращать ошибку, если `Racer` занимает больше 10 секунд.

## Сначала напишите тест

```go
func TestRacer(t *testing.T) {
	t.Run("compares speeds of servers, returning the url of the fastest one", func(t *testing.T) {
		slowServer := makeDelayedServer(20 * time.Millisecond)
		fastServer := makeDelayedServer(0 * time.Millisecond)

		defer slowServer.Close()
		defer fastServer.Close()

		slowURL := slowServer.URL
		fastURL := fastServer.URL

		want := fastURL
		got, _ := Racer(slowURL, fastURL)

		if got != want {
			t.Errorf("got %q, want %q", got, want)
		}
	})

	t.Run("returns an error if a server doesn't respond within 10s", func(t *testing.T) {
		serverA := makeDelayedServer(11 * time.Second)
		serverB := makeDelayedServer(12 * time.Second)

		defer serverA.Close()
		defer serverB.Close()

		_, err := Racer(serverA.URL, serverB.URL)

		if err == nil {
			t.Error("expected an error but didn't get one")
		}
	})
}
```

Мы заставили наши тестовые серверы возвращать ответ дольше 10 секунд, чтобы проверить этот сценарий, и ожидаем, что `Racer` теперь вернет два значения: выигрышный URL-адрес (который мы игнорируем в этом тесте с `_`) и `error`.

Обратите внимание, что мы также обработали возвращаемую ошибку в нашем первоначальном тесте, мы используем `_` пока, чтобы убедиться, что тесты будут работать.

## Попробуйте запустить тест

`./racer_test.go:37:10: assignment mismatch: 2 variables but Racer returns 1 value`

## Напишите минимальное количество кода, чтобы тест запустился, и проверьте вывод неудачного теста

```go
func Racer(a, b string) (winner string, error error) {
	select {
	case <-ping(a):
		return a, nil
	case <-ping(b):
		return b, nil
	}
}
```

Измените сигнатуру `Racer`, чтобы он возвращал победителя и `error`. Возвращайте `nil` для наших успешных случаев.

Если вы запустите его сейчас, через 11 секунд он завершится ошибкой.

```
--- FAIL: TestRacer (12.00s)
    --- FAIL: TestRacer/returns_an_error_if_a_server_doesn't_respond_within_10s (12.00s)
        racer_test.go:40: expected an error but didn't get one
```

## Напишите достаточно кода, чтобы тест прошел

```go
func Racer(a, b string) (winner string, error error) {
	select {
	case <-ping(a):
		return a, nil
	case <-ping(b):
		return b, nil
	case <-time.After(10 * time.Second):
		return "", fmt.Errorf("timed out waiting for %s and %s", a, b)
	}
}
```

`time.After` — очень удобная функция при использовании `select`. Хотя в нашем случае этого не произошло, вы потенциально можете написать код, который блокируется навсегда, если каналы, которые вы слушаете, никогда не возвращают значение. `time.After` возвращает `chan` (как `ping`) и отправит сигнал по нему по истечении определенного вами времени.

Для нас это идеально; если `a` или `b` успевают вернуться, они выигрывают, но если проходит 10 секунд, то наш `time.After` отправит сигнал, и мы вернем `error`.

### Медленные тесты

Проблема, с которой мы сталкиваемся, заключается в том, что этот тест занимает 10 секунд. Для такой простой логики это не кажется хорошим.

Что мы можем сделать, так это сделать таймаут настраиваемым. Таким образом, в нашем тесте мы можем иметь очень короткий таймаут, а затем, когда код будет использоваться в реальном мире, его можно будет установить на 10 секунд.

```go
func Racer(a, b string, timeout time.Duration) (winner string, error error) {
	select {
	case <-ping(a):
		return a, nil
	case <-ping(b):
		return b, nil
	case <-time.After(timeout):
		return "", fmt.Errorf("timed out waiting for %s and %s", a, b)
	}
}
```

Наши тесты теперь не скомпилируются, потому что мы не предоставляем таймаут.

Прежде чем спешить добавлять это значение по умолчанию в оба наших теста, давайте _прислушаемся к ним_.

-   Волнует ли нас таймаут в "успешном" тесте?
-   Требования были явными относительно таймаута.

Учитывая эти знания, давайте сделаем небольшой рефакторинг, чтобы угодить как нашим тестам, так и пользователям нашего кода.

```go
var tenSecondTimeout = 10 * time.Second

func Racer(a, b string) (winner string, error error) {
	return ConfigurableRacer(a, b, tenSecondTimeout)
}

func ConfigurableRacer(a, b string, timeout time.Duration) (winner string, error error) {
	select {
	case <-ping(a):
		return a, nil
	case <-ping(b):
		return b, nil
	case <-time.After(timeout):
		return "", fmt.Errorf("timed out waiting for %s and %s", a, b)
	}
}
```

Наши пользователи и наш первый тест могут использовать `Racer` (который использует `ConfigurableRacer` под капотом), а наш "несчастливый" тест может использовать `ConfigurableRacer`.

```go
func TestRacer(t *testing.T) {

	t.Run("compares speeds of servers, returning the url of the fastest one", func(t *testing.T) {
		slowServer := makeDelayedServer(20 * time.Millisecond)
		fastServer := makeDelayedServer(0 * time.Millisecond)

		defer slowServer.Close()
		defer fastServer.Close()

		slowURL := slowServer.URL
		fastURL := fastServer.URL

		want := fastURL
		got, err := Racer(slowURL, fastURL)

		if err != nil {
			t.Fatalf("did not expect an error but got one %v", err)
		}

		if got != want {
			t.Errorf("got %q, want %q", got, want)
		}
	})

	t.Run("returns an error if a server doesn't respond within the specified time", func(t *testing.T) {
		server := makeDelayedServer(25 * time.Millisecond)

		defer server.Close()

		_, err := ConfigurableRacer(server.URL, server.URL, 20*time.Millisecond)

		if err == nil {
			t.Error("expected an error but didn't get one")
		}
	})
}
```

Я добавил одну последнюю проверку в первый тест, чтобы убедиться, что мы не получаем `error`.

## Подведение итогов

### `select`

-   Помогает ждать на нескольких каналах.
-   Иногда вы захотите включить `time.After` в один из ваших `case`, чтобы предотвратить вечную блокировку вашей системы.

### `httptest`

-   Удобный способ создания тестовых серверов, чтобы у вас были надежные и управляемые тесты.
-   Использует те же интерфейсы, что и "настоящие" серверы `net/http`, что является согласованным и требует меньше обучения.