# JSON, маршрутизация и встраивание

**[Весь код для этой главы вы можете найти здесь](https://github.com/quii/learn-go-with-tests/tree/main/json)**

[В предыдущей главе](http-server.md) мы создали веб-сервер для хранения количества выигранных игр игроками.

У нашего владельца продукта (product owner) появилось новое требование: создать новую конечную точку (`endpoint`) под названием `/league`, которая будет возвращать список всех хранящихся игроков. Она хотела бы, чтобы данные возвращались в формате JSON.

## Вот код, который у нас есть на данный момент

```go
// server.go
package main

import (
	"fmt"
	"net/http"
	"strings"
)

type PlayerStore interface {
	GetPlayerScore(name string) int
	RecordWin(name string)
}

type PlayerServer struct {
	store PlayerStore
}

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

```go
// in_memory_player_store.go
package main

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

Соответствующие тесты вы можете найти по ссылке в начале главы.

Мы начнем с создания конечной точки для таблицы лиги.

## Сначала напишите тест

Мы расширим существующий набор тестов, так как у нас есть несколько полезных тестовых функций и фейковый `PlayerStore`, который можно использовать.

```go
//server_test.go
func TestLeague(t *testing.T) {
	store := StubPlayerStore{}
	server := &PlayerServer{&store}

	t.Run("it returns 200 on /league", func(t *testing.T) {
		request, _ := http.NewRequest(http.MethodGet, "/league", nil)
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		assertStatus(t, response.Code, http.StatusOK)
	})
}
```

Прежде чем беспокоиться о реальных очках и JSON, мы постараемся сохранить изменения минимальными, планируя итеративно двигаться к нашей цели. Самый простой старт — это проверить, что мы можем обратиться к `/league` и получить в ответ `OK`.

## Попробуйте запустить тест

```
    --- FAIL: TestLeague/it_returns_200_on_/league (0.00s)
        server_test.go:101: status code is wrong: got 404, want 200
FAIL
FAIL	playerstore	0.221s
FAIL
```

Наш `PlayerServer` возвращает `404 Not Found`, как будто мы пытались получить количество побед неизвестного игрока. Глядя на то, как `server.go` реализует `ServeHTTP`, мы понимаем, что он всегда предполагает вызов с URL, указывающим на конкретного игрока:

```go
player := strings.TrimPrefix(r.URL.Path, "/players/")
```

В предыдущей главе мы упоминали, что это довольно наивный способ маршрутизации. Наш тест правильно информирует нас о том, что нам нужна концепция обработки различных путей запросов.

## Напишите достаточно кода, чтобы тест прошел

Go имеет встроенный механизм маршрутизации под названием [`ServeMux`](https://golang.org/pkg/net/http/#ServeMux) (мультиплексор запросов), который позволяет привязывать `http.Handler`ы к определенным путям запросов.

Давайте пойдем на небольшие уступки и сделаем так, чтобы тесты прошли максимально быстро, зная, что мы сможем безопасно провести рефакторинг, как только тесты будут успешно пройдены.

```go
//server.go
func (p *PlayerServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {

	router := http.NewServeMux()

	router.Handle("/league", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	router.Handle("/players/", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		player := strings.TrimPrefix(r.URL.Path, "/players/")

		switch r.Method {
		case http.MethodPost:
			p.processWin(w, player)
		case http.MethodGet:
			p.showScore(w, player)
		}
	}))

	router.ServeHTTP(w, r)
}
```

- Когда запрос начинается, мы создаем маршрутизатор, а затем указываем ему, что для пути `x` использовать обработчик `y`.
- Таким образом, для нашей новой конечной точки мы используем `http.HandlerFunc` и _анонимную функцию_ для вызова `w.WriteHeader(http.StatusOK)` при запросе `/league`, чтобы наш новый тест прошел.
- Для маршрута `/players/` мы просто вырезаем и вставляем наш код в другой `http.HandlerFunc`.
- Наконец, мы обрабатываем входящий запрос, вызывая `ServeHTTP` нашего нового маршрутизатора (обратите внимание, что `ServeMux` _также_ является `http.Handler`?).

Тесты теперь должны пройти.

## Рефакторинг

`ServeHTTP` выглядит довольно большим, мы можем немного разделить его, выделив наши обработчики в отдельные методы.

```go
//server.go
func (p *PlayerServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {

	router := http.NewServeMux()
	router.Handle("/league", http.HandlerFunc(p.leagueHandler))
	router.Handle("/players/", http.HandlerFunc(p.playersHandler))

	router.ServeHTTP(w, r)
}

func (p *PlayerServer) leagueHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
}

func (p *PlayerServer) playersHandler(w http.ResponseWriter, r *http.Request) {
	player := strings.TrimPrefix(r.URL.Path, "/players/")

	switch r.Method {
	case http.MethodPost:
		p.processWin(w, player)
	case http.MethodGet:
		p.showScore(w, player)
	}
}
```

Довольно странно (и неэффективно) настраивать маршрутизатор при каждом входящем запросе, а затем вызывать его. В идеале мы хотим иметь некую функцию `NewPlayerServer`, которая будет принимать наши зависимости и выполнять однократную настройку маршрутизатора. Каждый запрос затем сможет использовать этот единственный экземпляр маршрутизатора.

```go
//server.go
type PlayerServer struct {
	store  PlayerStore
	router *http.ServeMux
}

func NewPlayerServer(store PlayerStore) *PlayerServer {
	p := &PlayerServer{
		store,
		http.NewServeMux(),
	}

	p.router.Handle("/league", http.HandlerFunc(p.leagueHandler))
	p.router.Handle("/players/", http.HandlerFunc(p.playersHandler))

	return p
}

func (p *PlayerServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	p.router.ServeHTTP(w, r)
}
```

- Теперь `PlayerServer` должен хранить маршрутизатор.
- Мы переместили создание маршрутизации из `ServeHTTP` в наш `NewPlayerServer`, так что это нужно делать только один раз, а не для каждого запроса.
- Вам нужно будет обновить весь тестовый и производственный код, где мы раньше использовали `PlayerServer{&store}`, на `NewPlayerServer(&store)`.

### Последний рефакторинг

Попробуйте изменить код следующим образом.

```go
type PlayerServer struct {
	store PlayerStore
	http.Handler
}

func NewPlayerServer(store PlayerStore) *PlayerServer {
	p := new(PlayerServer)

	p.store = store

	router := http.NewServeMux()
	router.Handle("/league", http.HandlerFunc(p.leagueHandler))
	router.Handle("/players/", http.HandlerFunc(p.playersHandler))

	p.Handler = router

	return p
}
```

Затем замените `server := &PlayerServer{&store}` на `server := NewPlayerServer(&store)` в `server_test.go`, `server_integration_test.go` и `main.go`.

Наконец, убедитесь, что вы **удалили** `func (p *PlayerServer) ServeHTTP(w http.ResponseWriter, r *http.Request)`, так как она больше не нужна!

## Встраивание

Мы изменили второе свойство структуры `PlayerServer`, удалив именованное свойство `router http.ServeMux` и заменив его на `http.Handler`; это называется _встраиванием_ (embedding).

> Go не предоставляет типичное, управляемое типами понятие наследования (subclassing), но имеет возможность «заимствовать» части реализации путем встраивания типов в структуру (struct) или интерфейс (interface).

[Effective Go - Встраивание](https://golang.org/doc/effective_go.html#embedding)

Это означает, что наш `PlayerServer` теперь обладает всеми методами, которые есть у `http.Handler`, а это просто `ServeHTTP`.

Чтобы «заполнить» `http.Handler`, мы присваиваем ему `router`, который мы создаем в `NewPlayerServer`. Мы можем это сделать, потому что `http.ServeMux` имеет метод `ServeHTTP`.

Это позволяет нам удалить наш собственный метод `ServeHTTP`, поскольку мы уже предоставляем его через встроенный тип.

Встраивание — очень интересная языковая особенность. Вы можете использовать его с интерфейсами для создания новых интерфейсов.

```go
type Animal interface {
	Eater
	Sleeper
}
```

И вы можете использовать его также с конкретными типами, а не только с интерфейсами. Как и ожидается, если вы встраиваете конкретный тип, у вас будет доступ ко всем его публичным методам и полям.

### Есть ли недостатки?

Вы должны быть осторожны при встраивании типов, потому что вы будете раскрывать все публичные методы и поля встраиваемого типа. В нашем случае это нормально, потому что мы встроили только тот _интерфейс_, который хотели раскрыть (`http.Handler`).

Если бы мы были ленивы и встроили `http.ServeMux` вместо него (конкретный тип), это все равно работало бы, _но_ пользователи `PlayerServer` смогли бы добавлять новые маршруты на наш сервер, потому что `Handle(path, handler)` был бы публичным.

**При встраивании типов всегда тщательно обдумывайте, какое влияние это оказывает на ваш публичный API.**

Это _очень_ распространенная ошибка — неправильно использовать встраивание и в итоге засорять свои API, раскрывая внутреннее устройство вашего типа.

Теперь, когда мы перестроили наше приложение, мы можем легко добавлять новые маршруты и у нас есть начало для конечной точки `/league`. Теперь нам нужно заставить ее возвращать полезную информацию.

Мы должны возвращать JSON, который выглядит примерно так.

```json
[
   {
      "Name":"Bill",
      "Wins":10
   },
   {
      "Name":"Alice",
      "Wins":15
   }
]
```

## Сначала напишите тест

Мы начнем с попытки разобрать ответ в нечто осмысленное.

```go
//server_test.go
func TestLeague(t *testing.T) {
	store := StubPlayerStore{}
	server := NewPlayerServer(&store)

	t.Run("it returns 200 on /league", func(t *testing.T) {
		request, _ := http.NewRequest(http.MethodGet, "/league", nil)
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		var got []Player

		err := json.NewDecoder(response.Body).Decode(&got)

		if err != nil {
			t.Fatalf("Unable to parse response from server %q into slice of Player, '%v'", response.Body, err)
		}

		assertStatus(t, response.Code, http.StatusOK)
	})
}
```

### Почему не тестировать JSON-строку?

Можно утверждать, что более простым начальным шагом было бы просто проверить, что тело ответа содержит определенную JSON-строку.

По моему опыту, тесты, которые проверяют JSON-строки, имеют следующие проблемы.

- *Хрупкость*. Если вы измените модель данных, ваши тесты упадут.
- *Сложность отладки*. Может быть трудно понять, в чем заключается реальная проблема при сравнении двух JSON-строк.
- *Нечеткая цель*. Хотя вывод должен быть JSON, действительно важно именно то, какие данные, а не то, как они закодированы.
- *Повторное тестирование стандартной библиотеки*. Нет необходимости проверять, как стандартная библиотека выводит JSON, это уже протестировано. Не тестируйте чужой код.

Вместо этого мы должны стремиться разбирать JSON в структуры данных, которые релевантны для наших тестов.

### Моделирование данных

Учитывая модель данных JSON, похоже, нам нужен массив `Player` с некоторыми полями, поэтому мы создали новый тип для этого.

```go
//server.go
type Player struct {
	Name string
	Wins int
}
```

### Декодирование JSON

```go
//server_test.go
var got []Player
err := json.NewDecoder(response.Body).Decode(&got)
```

Чтобы разобрать JSON в нашу модель данных, мы создаем `Decoder` из пакета `encoding/json`, а затем вызываем его метод `Decode`. Для создания `Decoder` нужен `io.Reader`, из которого он будет читать, и в нашем случае это `Body` нашего шпиона ответа.

`Decode` принимает адрес того, во что мы пытаемся декодировать, поэтому мы объявляем пустой срез `Player` строкой ранее.

Разбор JSON может завершиться неудачей, поэтому `Decode` может вернуть `error`. Нет смысла продолжать тест, если он не удастся, поэтому мы проверяем ошибку и останавливаем тест с помощью `t.Fatalf`, если это происходит. Обратите внимание, что мы выводим тело ответа вместе с ошибкой, так как важно, чтобы тот, кто запускает тест, видел, какая строка не может быть разобрана.

## Попробуйте запустить тест

```
=== RUN   TestLeague/it_returns_200_on_/league
    --- FAIL: TestLeague/it_returns_200_on_/league (0.00s)
        server_test.go:107: Unable to parse response from server '' into slice of Player, 'unexpected end of JSON input'
```

Наша конечная точка в настоящее время не возвращает тело, поэтому его нельзя разобрать в JSON.

## Напишите достаточно кода, чтобы тест прошел

```go
//server.go
func (p *PlayerServer) leagueHandler(w http.ResponseWriter, r *http.Request) {
	leagueTable := []Player{
		{"Chris", 20},
	}

	json.NewEncoder(w).Encode(leagueTable)

	w.WriteHeader(http.StatusOK)
}
```

Тест теперь проходит.

### Кодирование и декодирование

Обратите внимание на прекрасную симметрию в стандартной библиотеке.

- Чтобы создать `Encoder`, вам нужен `io.Writer`, который реализует `http.ResponseWriter`.
- Чтобы создать `Decoder`, вам нужен `io.Reader`, который реализует поле `Body` нашего шпиона ответа.

На протяжении всей этой книги мы использовали `io.Writer`, и это еще одна демонстрация его распространенности в стандартной библиотеке и того, как многие библиотеки легко работают с ним.

## Рефакторинг

Было бы неплохо разделить задачи между нашим обработчиком и получением `leagueTable`, поскольку мы знаем, что очень скоро перестанем жестко кодировать это.

```go
//server.go
func (p *PlayerServer) leagueHandler(w http.ResponseWriter, r *http.Request) {
	json.NewEncoder(w).Encode(p.getLeagueTable())
	w.WriteHeader(http.StatusOK)
}

func (p *PlayerServer) getLeagueTable() []Player {
	return []Player{
		{"Chris", 20},
	}
}
```

Далее мы захотим расширить наш тест, чтобы мы могли точно контролировать, какие данные мы хотим получить обратно.

## Сначала напишите тест

Мы можем обновить тест, чтобы убедиться, что таблица лиги содержит игроков, которых мы будем заглушать в нашем хранилище.

Обновите `StubPlayerStore`, чтобы он мог хранить лигу, которая представляет собой просто срез `Player`. Мы будем хранить наши ожидаемые данные там.

```go
//server_test.go
type StubPlayerStore struct {
	scores   map[string]int
	winCalls []string
	league   []Player
}
```

Затем обновите наш текущий тест, добавив несколько игроков в свойство `league` нашего заглушки и убедитесь, что они возвращаются с нашего сервера.

```go
//server_test.go
func TestLeague(t *testing.T) {

	t.Run("it returns the league table as JSON", func(t *testing.T) {
		wantedLeague := []Player{
			{"Cleo", 32},
			{"Chris", 20},
			{"Tiest", 14},
		}

		store := StubPlayerStore{nil, nil, wantedLeague}
		server := NewPlayerServer(&store)

		request, _ := http.NewRequest(http.MethodGet, "/league", nil)
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		var got []Player

		err := json.NewDecoder(response.Body).Decode(&got)

		if err != nil {
			t.Fatalf("Unable to parse response from server %q into slice of Player, '%v'", response.Body, err)
		}

		assertStatus(t, response.Code, http.StatusOK)

		if !reflect.DeepEqual(got, wantedLeague) {
			t.Errorf("got %v want %v", got, wantedLeague)
		}
	})
}
```

## Попробуйте запустить тест

```
./server_test.go:33:3: too few values in struct initializer
./server_test.go:70:3: too few values in struct initializer
```

## Напишите минимальное количество кода, чтобы тест запустился и проверьте вывод упавшего теста

Вам нужно будет обновить другие тесты, так как у нас появилось новое поле в `StubPlayerStore`; установите его в `nil` для других тестов.

Попробуйте запустить тесты снова, и вы должны получить:

```
=== RUN   TestLeague/it_returns_the_league_table_as_JSON
    --- FAIL: TestLeague/it_returns_the_league_table_as_JSON (0.00s)
        server_test.go:124: got [{Chris 20}] want [{Cleo 32} {Chris 20} {Tiest 14}]
```

## Напишите достаточно кода, чтобы тест прошел

Мы знаем, что данные находятся в нашем `StubPlayerStore`, и мы абстрагировали это в интерфейс `PlayerStore`. Нам нужно обновить его, чтобы любой, кто передает нам `PlayerStore`, мог предоставить данные для лиг.

```go
//server.go
type PlayerStore interface {
	GetPlayerScore(name string) int
	RecordWin(name string)
	GetLeague() []Player
}
```

Теперь мы можем обновить код нашего обработчика, чтобы он вызывал этот метод вместо возврата жестко закодированного списка. Удалите наш метод `getLeagueTable()` и затем обновите `leagueHandler`, чтобы он вызывал `GetLeague()`.

```go
//server.go
func (p *PlayerServer) leagueHandler(w http.ResponseWriter, r *http.Request) {
	json.NewEncoder(w).Encode(p.store.GetLeague())
	w.WriteHeader(http.StatusOK)
}
```

Попробуйте запустить тесты.

```
# github.com/quii/learn-go-with-tests/json-and-io/v4
./main.go:9:50: cannot use NewInMemoryPlayerStore() (type *InMemoryPlayerStore) as type PlayerStore in argument to NewPlayerServer:
    *InMemoryPlayerStore does not implement PlayerStore (missing GetLeague method)
./server_integration_test.go:11:27: cannot use store (type *InMemoryPlayerStore) as type PlayerStore in argument to NewPlayerServer:
    *InMemoryPlayerStore does not implement PlayerStore (missing GetLeague method)
./server_test.go:36:28: cannot use &store (type *StubPlayerStore) as type PlayerStore in argument to NewPlayerServer:
    *StubPlayerStore does not implement PlayerStore (missing GetLeague method)
./server_test.go:74:28: cannot use &store (type *StubPlayerStore) as type PlayerStore in argument to NewPlayerServer:
    *StubPlayerStore does not implement PlayerStore (missing GetLeague method)
./server_test.go:106:29: cannot use &store (type *StubPlayerStore) as type PlayerStore in argument to NewPlayerServer:
    *StubPlayerStore does not implement PlayerStore (missing GetLeague method)
```

Компилятор жалуется, потому что `InMemoryPlayerStore` и `StubPlayerStore` не имеют нового метода, который мы добавили в наш интерфейс.

Для `StubPlayerStore` это довольно просто, просто верните поле `league`, которое мы добавили ранее.

```go
//server_test.go
func (s *StubPlayerStore) GetLeague() []Player {
	return s.league
}
```

Вот напоминание о том, как реализован `InMemoryStore`.

```go
//in_memory_player_store.go
type InMemoryPlayerStore struct {
	store map[string]int
}
```

Хотя было бы довольно просто реализовать `GetLeague` «правильно», итерируя по отображению, помните, что мы просто пытаемся _написать минимальное количество кода, чтобы тесты прошли_.

Так что давайте пока просто сделаем компилятор счастливым и смиримся с неприятным ощущением неполной реализации в нашем `InMemoryStore`.

```go
//in_memory_player_store.go
func (i *InMemoryPlayerStore) GetLeague() []Player {
	return nil
}
```

На самом деле это говорит нам о том, что _позже_ мы захотим это протестировать, но давайте пока отложим это.

Попробуйте запустить тесты, компилятор должен пройти, и тесты должны быть пройдены!

## Рефакторинг

Тестовый код не очень хорошо передает наши намерения и содержит много шаблонного кода, который мы можем убрать с помощью рефакторинга.

```go
//server_test.go
t.Run("it returns the league table as JSON", func(t *testing.T) {
	wantedLeague := []Player{
		{"Cleo", 32},
		{"Chris", 20},
		{"Tiest", 14},
	}

	store := StubPlayerStore{nil, nil, wantedLeague}
	server := NewPlayerServer(&store)

	request := newLeagueRequest()
	response := httptest.NewRecorder()

	server.ServeHTTP(response, request)

	got := getLeagueFromResponse(t, response.Body)
	assertStatus(t, response.Code, http.StatusOK)
	assertLeague(t, got, wantedLeague)
})
```

Вот новые вспомогательные функции:

```go
//server_test.go
func getLeagueFromResponse(t testing.TB, body io.Reader) (league []Player) {
	t.Helper()
	err := json.NewDecoder(body).Decode(&league)

	if err != nil {
		t.Fatalf("Unable to parse response from server %q into slice of Player, '%v'", body, err)
	}

	return
}

func assertLeague(t testing.TB, got, want []Player) {
	t.Helper()
	if !reflect.DeepEqual(got, want) {
		t.Errorf("got %v want %v", got, want)
	}
}

func newLeagueRequest() *http.Request {
	req, _ := http.NewRequest(http.MethodGet, "/league", nil)
	return req
}
```

Последнее, что нам нужно сделать для работы нашего сервера, — это убедиться, что мы возвращаем заголовок `content-type` в ответе, чтобы машины могли распознать, что мы возвращаем `JSON`.

## Сначала напишите тест

Добавьте это утверждение к существующему тесту:

```go
//server_test.go
if response.Result().Header.Get("content-type") != "application/json" {
	t.Errorf("response did not have content-type of application/json, got %v", response.Result().Header)
}
```

## Попробуйте запустить тест

```
=== RUN   TestLeague/it_returns_the_league_table_as_JSON
    --- FAIL: TestLeague/it_returns_the_league_table_as_JSON (0.00s)
        server_test.go:124: response did not have content-type of application/json, got map[Content-Type:[text/plain; charset=utf-8]]
```

## Напишите достаточно кода, чтобы тест прошел

Обновите `leagueHandler`:

```go
//server.go
func (p *PlayerServer) leagueHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("content-type", "application/json")
	json.NewEncoder(w).Encode(p.store.GetLeague())
}
```

Тест должен пройти.

## Рефакторинг

Создайте константу для "application/json" и используйте ее в `leagueHandler`:

```go
//server.go
const jsonContentType = "application/json"

func (p *PlayerServer) leagueHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("content-type", jsonContentType)
	json.NewEncoder(w).Encode(p.store.GetLeague())
}
```

Затем добавьте вспомогательную функцию для `assertContentType`.

```go
//server_test.go
func assertContentType(t testing.TB, response *httptest.ResponseRecorder, want string) {
	t.Helper()
	if response.Result().Header.Get("content-type") != want {
		t.Errorf("response did not have content-type of %s, got %v", want, response.Result().Header)
	}
}
```

Используйте ее в тесте.

```go
//server_test.go
assertContentType(t, response, jsonContentType)
```

Теперь, когда мы разобрались с `PlayerServer`, мы можем обратить внимание на `InMemoryPlayerStore`, потому что прямо сейчас, если мы попробуем продемонстрировать это владельцу продукта, `/league` не будет работать.

Самый быстрый способ получить некоторую уверенность — это добавить в наш интеграционный тест: мы можем обратиться к новой конечной точке и проверить, что получаем правильный ответ от `/league`.

## Сначала напишите тест

Мы можем использовать `t.Run`, чтобы немного разбить этот тест, и мы можем повторно использовать вспомогательные функции из наших серверных тестов — это еще раз показывает важность рефакторинга тестов.

```go
//server_integration_test.go
func TestRecordingWinsAndRetrievingThem(t *testing.T) {
	store := NewInMemoryPlayerStore()
	server := NewPlayerServer(store)
	player := "Pepper"

	server.ServeHTTP(httptest.NewRecorder(), newPostWinRequest(player))
	server.ServeHTTP(httptest.NewRecorder(), newPostWinRequest(player))
	server.ServeHTTP(httptest.NewRecorder(), newPostWinRequest(player))

	t.Run("get score", func(t *testing.T) {
		response := httptest.NewRecorder()
		server.ServeHTTP(response, newGetScoreRequest(player))
		assertStatus(t, response.Code, http.StatusOK)

		assertResponseBody(t, response.Body.String(), "3")
	})

	t.Run("get league", func(t *testing.T) {
		response := httptest.NewRecorder()
		server.ServeHTTP(response, newLeagueRequest())
		assertStatus(t, response.Code, http.StatusOK)

		got := getLeagueFromResponse(t, response.Body)
		want := []Player{
			{"Pepper", 3},
		}
		assertLeague(t, got, want)
	})
}
```

## Попробуйте запустить тест

```
=== RUN   TestRecordingWinsAndRetrievingThem/get_league
    --- FAIL: TestRecordingWinsAndRetrievingThem/get_league (0.00s)
        server_integration_test.go:35: got [] want [{Pepper 3}]
```

## Напишите достаточно кода, чтобы тест прошел

`InMemoryPlayerStore` возвращает `nil` при вызове `GetLeague()`, поэтому нам нужно это исправить.

```go
//in_memory_player_store.go
func (i *InMemoryPlayerStore) GetLeague() []Player {
	var league []Player
	for name, wins := range i.store {
		league = append(league, Player{name, wins})
	}
	return league
}
```

Всё, что нам нужно сделать, это итерировать по отображению и преобразовать каждую пару ключ/значение в `Player`.

Тест теперь должен пройти.

## Подведение итогов

Мы продолжили безопасно итеративно развивать нашу программу, используя TDD, добавив поддержку новых конечных точек поддерживаемым способом с помощью маршрутизатора, и теперь она может возвращать JSON для наших потребителей. В следующей главе мы рассмотрим сохранение данных и сортировку нашей лиги.

Что мы рассмотрели:

- **Маршрутизация (Routing)**. Стандартная библиотека предлагает простой в использовании тип для маршрутизации. Она полностью поддерживает интерфейс `http.Handler` тем, что вы назначаете маршруты `Handler`ам, и сам маршрутизатор также является `Handler`ом. Однако у нее нет некоторых функций, которые вы могли бы ожидать, таких как переменные пути (например, `/users/{id}`). Вы можете легко разобрать эту информацию самостоятельно, но вам, возможно, стоит рассмотреть другие библиотеки маршрутизации, если это станет обузой. Большинство популярных из них придерживаются философии стандартной библиотеки, также реализуя `http.Handler`.
- **Встраивание типов (Type embedding)**. Мы немного коснулись этой техники, но вы можете [узнать о ней больше в Effective Go](https://golang.org/doc/effective_go.html#embedding). Если есть одна вещь, которую вы должны усвоить из этого, это то, что она может быть чрезвычайно полезной, но _всегда думайте о своем публичном API, раскрывайте только то, что уместно_.
- **Десериализация и сериализация JSON**. Стандартная библиотека делает очень простой сериализацию и десериализацию ваших данных. Она также открыта для настройки, и вы можете настроить, как работают эти преобразования данных, если это необходимо.