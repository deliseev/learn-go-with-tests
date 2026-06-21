# Оператор Select

**[Весь код для этой главы можно найти здесь](https://github.com/quii/learn-go-with-tests/tree/main/select)**

Вам было предложено создать функцию `WebsiteRacer`, которая принимает два URL-адреса и "соревнуется" между ними, выполняя HTTP GET-запросы к ним и возвращая URL-адрес, который ответил первым. Если ни один из них не ответит в течение 10 секунд, функция должна вернуть `error`.

Для этого мы будем использовать:

- `net/http` для выполнения HTTP-вызовов.
- `net/http/httptest` для помощи в их тестировании.
- горутины.
- `select` для синхронизации процессов.

## Сначала напишите тест

Начнем с чего-то простого, чтобы положить начало.

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

Мы знаем, что это не идеально и имеет проблемы, но это начало. Важно не зацикливаться на том, чтобы все было идеально с первого раза.

## Попробуйте запустить тест

`./racer_test.go:14:9: undefined: Racer`

## Напишите минимальный объем кода для запуска теста и проверьте вывод ошибочного теста

```go
func Racer(a, b string) (winner string) {
	return
}
```

`racer_test.go:25: got '', want 'http://www.quii.dev'`

## Напишите достаточный код, чтобы тест прошел

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

1. Мы используем `time.Now()` для записи времени непосредственно перед попыткой получить `URL`.
1. Затем мы используем [`http.Get`](https://golang.org/pkg/net/http/#Client.Get), чтобы попытаться выполнить HTTP `GET` запрос к `URL`. Эта функция возвращает [`http.Response`](https://golang.org/pkg/net/http/#Response) и `error`, но пока нам не интересны эти значения.
1. `time.Since` принимает начальное время и возвращает `time.Duration` разницы.

После этого мы просто сравниваем продолжительность, чтобы увидеть, какая из них быстрее.

### Проблемы

Это может привести к прохождению теста или нет. Проблема в том, что мы обращаемся к реальным веб-сайтам для тестирования нашей собственной логики.

Тестирование кода, использующего HTTP, настолько распространено, что Go имеет инструменты в стандартной библиотеке, чтобы помочь вам в этом.

В главах, посвященных мокированию и внедрению зависимостей, мы обсуждали, что в идеале мы не хотим полагаться на внешние сервисы для тестирования нашего кода, потому что они могут быть

- Медленными
- Ненадежными
- Не позволяют тестировать граничные случаи

В стандартной библиотеке есть пакет [`net/http/httptest`](https://golang.org/pkg/net/http/httptest/), который позволяет пользователям легко создавать имитирующий (mock) HTTP-сервер.

Давайте изменим наши тесты, чтобы использовать имитации (mocks), так что у нас будут надежные серверы для тестирования, которыми мы можем управлять.

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

На самом деле это означает, что требуется функция, которая принимает `ResponseWriter` и `Request`, что не слишком удивительно для HTTP-сервера.

Оказывается, здесь нет никакой дополнительной магии, **именно так вы бы написали _настоящий_ HTTP-сервер на Go**. Единственное отличие состоит в том, что мы оборачиваем его в `httptest.NewServer`, что упрощает использование при тестировании, так как он находит открытый порт для прослушивания, а затем вы можете закрыть его, когда закончите тест.

Внутри наших двух серверов мы заставляем медленный сервер использовать короткую задержку `time.Sleep` при получении запроса, чтобы сделать его медленнее, чем другой. Затем оба сервера отправляют `OK`-ответ с `w.WriteHeader(http.StatusOK)` обратно вызывающему.

Если вы перезапустите тест, он теперь определенно пройдет и должен быть быстрее. Поиграйте с этими задержками, чтобы намеренно сломать тест.

## Рефакторинг

У нас есть некоторое дублирование как в производственном коде, так и в тестовом коде.

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

Такое устранение дублирования (DRY) делает наш код `Racer` гораздо более читабельным.

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

Мы провели рефакторинг создания наших фиктивных серверов в функцию `makeDelayedServer`, чтобы вынести часть неинтересного кода из теста и уменьшить повторения.

### `defer`

Предварив вызов функции словом `defer`, эта функция будет вызвана _в конце содержащей ее функции_.

Иногда вам потребуется освободить ресурсы, например, закрыть файл или, в нашем случае, закрыть сервер, чтобы он не продолжал прослушивать порт.

Вы хотите, чтобы это выполнялось в конце функции, но при этом сохранить инструкцию рядом с местом создания сервера для удобства будущих читателей кода.

Наш рефакторинг является улучшением и разумным решением, учитывая уже рассмотренные возможности Go, но мы можем сделать решение проще.

### Синхронизация процессов

- Почему мы тестируем скорость веб-сайтов по очереди, когда Go отлично подходит для параллелизма? Мы должны быть в состоянии проверять оба одновременно.
- Нас на самом деле не интересует _точное время ответа_ на запросы, мы просто хотим знать, какой из них вернётся первым.

Для этого мы собираемся ввести новую конструкцию под названием `select`, которая помогает нам очень легко и понятно синхронизировать процессы.

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

В нашем случае нам _неважно_, какой тип отправляется в канал, _мы просто хотим сигнализировать о завершении_, и закрытие канала работает идеально!

Почему `struct{}`, а не другой тип, например `bool`? Ну, `chan struct{}` — это наименьший доступный тип данных с точки зрения памяти, поэтому мы
не получаем выделения памяти в отличие от `bool`. Поскольку мы закрываем канал и ничего в него не отправляем, зачем что-либо выделять?

Внутри той же функции мы запускаем горутину, которая отправит сигнал в этот канал, как только мы завершим `http.Get(url)`.

##### Всегда используйте `make` для каналов

Обратите внимание, что мы должны использовать `make` при создании канала; а не, скажем, `var ch chan struct{}`. При использовании `var` переменная будет инициализирована "нулевым" значением типа. Так, для `string` это `""`, для `int` это 0 и т.д.

Для каналов нулевое значение — это `nil`, и если вы попытаетесь отправить в него с помощью `<-`, он будет блокироваться вечно, потому что вы не можете отправлять в `nil` каналы.

[Вы можете увидеть это в действии в Go Playground](https://play.golang.org/p/IIbeAox5jKA)
#### `select`

Вы помните из главы о параллелизме, что вы можете ждать отправки значений в канал с помощью `myVar := <-ch`. Это _блокирующий_ вызов, поскольку вы ждете значения.

`select` позволяет ждать _нескольких_ каналов. Первый, кто отправит значение, "побеждает", и код, находящийся под `case`, выполняется.

Мы используем `ping` в нашем `select`, чтобы настроить два канала, по одному для каждого из наших `URL`. Тот, кто первым запишет в свой канал, приведет к выполнению своего кода в `select`, что приведет к возврату его `URL` (и объявлению его победителем).

После этих изменений замысел нашего кода очень ясен, а реализация на самом деле проще.

### Таймауты

Нашим последним требованием было возвращать ошибку, если выполнение `Racer` занимает более 10 секунд.

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

Мы сделали так, чтобы наши тестовые серверы отвечали дольше 10 секунд, чтобы отработать этот сценарий, и теперь мы ожидаем, что `Racer` вернёт два значения: выигрышный URL (который мы игнорируем в этом тесте с помощью `_`) и `error`.

Обратите внимание, что мы также обработали возвращаемую ошибку в нашем исходном тесте, используя `_` пока что для обеспечения запуска тестов.

## Попробуйте запустить тест

`./racer_test.go:37:10: assignment mismatch: 2 variables but Racer returns 1 value`

## Напишите минимальный объем кода для запуска теста и проверьте вывод ошибочного теста

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

Измените сигнатуру `Racer`, чтобы она возвращала победителя и `error`. Возвращайте `nil` для наших успешных случаев.

Компилятор будет жаловаться на ваш _первый тест_, который ищет только одно значение, поэтому измените эту строку на `got, err := Racer(slowURL, fastURL)`, зная, что мы должны проверить, что _не_ получаем ошибку в нашем успешном сценарии.

Если вы запустите его сейчас, через 11 секунд он завершится с ошибкой.

```
--- FAIL: TestRacer (12.00s)
    --- FAIL: TestRacer/returns_an_error_if_a_server_doesn't_respond_within_10s (12.00s)
        racer_test.go:40: expected an error but didn't get one
```

## Напишите достаточный код, чтобы тест прошел

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

`time.After` — очень удобная функция при использовании `select`. Хотя в нашем случае этого не произошло, вы потенциально можете написать код, который будет блокироваться вечно, если каналы, которые вы прослушиваете, никогда не возвращают значение. `time.After` возвращает `chan` (как `ping`) и отправит по нему сигнал по истечении заданного вами времени.

Для нас это идеально; если `a` или `b` успевают ответить, они выигрывают, но если мы достигаем 10 секунд, то наш `time.After` отправит сигнал, и мы вернем `error`.

### Медленные тесты

Проблема в том, что этот тест занимает 10 секунд. Для такой простой логики это не очень хорошо.

Что мы можем сделать, так это сделать таймаут настраиваемым. Таким образом, в нашем тесте мы можем установить очень короткий таймаут, а затем, когда код будет использоваться в реальном мире, его можно будет установить на 10 секунд.

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

Наши тесты теперь не будут компилироваться, потому что мы не предоставляем таймаут.

Прежде чем спешить добавлять это значение по умолчанию в оба наших теста, давайте _прислушаемся к ним_.

- Волнует ли нас таймаут в "успешном" тесте?
- Требования к таймауту были явными.

Учитывая эти знания, давайте проведем небольшой рефакторинг, чтобы учесть интересы как наших тестов, так и пользователей нашего кода.

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

Наши пользователи и наш первый тест могут использовать `Racer` (который внутри использует `ConfigurableRacer`), а наш тест "неудачного" пути может использовать `ConfigurableRacer`.

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

## Заключение

### `select`

- Помогает вам ждать на нескольких каналах.
- Иногда вы захотите включить `time.After` в один из ваших `cases`, чтобы предотвратить вечную блокировку вашей системы.

### `httptest`

- Удобный способ создания тестовых серверов, чтобы вы могли иметь надежные и контролируемые тесты.
- Использует те же интерфейсы, что и "реальные" `net/http` серверы, что обеспечивает согласованность и уменьшает объем изучаемого материала.
