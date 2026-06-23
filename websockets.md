# WebSockets

[**Весь код для этой главы можно найти здесь**](https://github.com/quii/learn-go-with-tests/tree/main/websockets)

В этой главе мы узнаем, как использовать WebSockets для улучшения нашего приложения.

## Обзор проекта

В нашей кодовой базе покера есть два приложения:

* _Консольное приложение (CLI)_. Предлагает пользователю ввести количество игроков в игре. После этого информирует игроков о значении «слепой ставки» (блайнда), которое со временем увеличивается. В любой момент пользователь может ввести `"{Playername} wins"`, чтобы завершить игру и записать победителя в хранилище.
* _Веб-приложение_. Позволяет пользователям записывать победителей игр и отображает турнирную таблицу. Использует то же хранилище, что и консольное приложение.

## Следующие шаги

Владелец продукта (product owner) в восторге от консольного приложения, но предпочла бы перенести этот функционал в браузер. Она представляет себе веб-страницу с текстовым полем, в котором пользователь вводит количество игроков, и после отправки формы на странице отображается значение блайнда, автоматически обновляющееся в нужное время. Как и в консольном приложении, пользователь может объявить победителя, и тот будет сохранен в базе данных.

На первый взгляд это звучит довольно просто, но, как всегда, мы должны сделать упор на _итеративный_ подход к написанию программного обеспечения.

Сначала нам нужно будет отдавать HTML. До сих пор все наши HTTP-эндпоинты возвращали либо простой текст, либо JSON. Мы _могли бы_ использовать те же методы, которые нам уже известны (поскольку все они в конечном итоге работают со строками), но мы также можем использовать пакет [html/template](https://golang.org/pkg/html/template/) для более чистого решения.

Нам также нужно иметь возможность асинхронно отправлять пользователю сообщения вида `The blind is now *y*` без необходимости перезагружать страницу в браузере. Для этого мы можем использовать [WebSockets](https://en.wikipedia.org/wiki/WebSocket).

> WebSocket — это компьютерный коммуникационный протокол, обеспечивающий каналы полнодуплексной связи поверх одного TCP-соединения.

Поскольку мы осваиваем сразу несколько технологий, тем более важно сначала сделать минимально возможный объем полезной работы, а затем развивать её итеративно.

По этой причине первым делом мы создадим веб-страницу с формой для записи победителя. Вместо отправки обычной формы мы будем использовать WebSockets для отправки этих данных на наш сервер для последующей записи.

После этого мы поработаем над оповещениями о блайндах, и к этому моменту у нас уже будет настроена некоторая базовая инфраструктура.

### Как насчет тестов для JavaScript?

Для реализации этого будет написан некоторый код на JavaScript, но я не буду углубляться в написание тестов для него.

Это, конечно, возможно, но ради краткости я не буду включать сюда какие-либо объяснения по этому поводу.

Извините, ребята. Потребуйте от O'Reilly заплатить мне за создание курса «Изучай JavaScript с помощью тестов» (Learn JavaScript with tests).

## Сначала напишите тест

Первое, что нам нужно сделать, — это отдавать пользователям HTML-страницу при переходе на `/game`.

Напомним соответствующий код нашего веб-сервера:

```go
type PlayerServer struct {
	store PlayerStore
	http.Handler
}

const jsonContentType = "application/json"

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

Самое _простое_, что мы можем сделать на данный момент, — это проверить, что при запросе `GET /game` мы получаем статус `200`.

```go
func TestGame(t *testing.T) {
	t.Run("GET /game returns 200", func(t *testing.T) {
		server := NewPlayerServer(&StubPlayerStore{})

		request, _ := http.NewRequest(http.MethodGet, "/game", nil)
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		assertStatus(t, response.Code, http.StatusOK)
	})
}
```

## Попробуйте запустить тест

```
--- FAIL: TestGame (0.00s)
=== RUN   TestGame/GET_/game_returns_200
    --- FAIL: TestGame/GET_/game_returns_200 (0.00s)
    	server_test.go:109: did not get correct status, got 404, want 200
```

## Напишите достаточно кода, чтобы тест прошел

На нашем сервере настроен роутер, так что это исправить относительно легко.

Добавьте в наш роутер:

```go
router.Handle("/game", http.HandlerFunc(p.game))
```

И затем напишите метод `game`:

```go
func (p *PlayerServer) game(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
}
```

## Рефакторинг

Код сервера уже в порядке, благодаря тому, что мы очень легко встроили новый код в существующий, хорошо структурированный код.

Мы можем немного улучшить тест, добавив вспомогательную тестовую функцию `newGameRequest` для выполнения запроса к `/game`. Попробуйте написать её самостоятельно.

```go
func TestGame(t *testing.T) {
	t.Run("GET /game returns 200", func(t *testing.T) {
		server := NewPlayerServer(&StubPlayerStore{})

		request := newGameRequest()
		response := httptest.NewRecorder()

		server.ServeHTTP(response, request)

		assertStatus(t, response, http.StatusOK)
	})
}
```

Вы также заметите, что я изменил `assertStatus`, чтобы эта функция принимала `response` вместо `response.Code`, так как, на мой взгляд, это лучше читается.

Теперь нам нужно сделать так, чтобы эндпоинт возвращал HTML. Вот он:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Let's play poker</title>
</head>
<body>
<section id="game">
    <div id="declare-winner">
        <label for="winner">Winner</label>
        <input type="text" id="winner"/>
        <button id="winner-button">Declare winner</button>
    </div>
</section>
</body>
<script type="application/javascript">

    const submitWinnerButton = document.getElementById('winner-button')
    const winnerInput = document.getElementById('winner')

    if (window['WebSocket']) {
        const conn = new WebSocket('ws://' + document.location.host + '/ws')

        submitWinnerButton.onclick = event => {
            conn.send(winnerInput.value)
        }
    }
</script>
</html>
```

У нас есть очень простая веб-страница:

* Текстовое поле ввода для указания победителя.
* Кнопка, на которую можно нажать, чтобы объявить победителя.
* Небольшой скрипт на JavaScript для открытия WebSocket-соединения с нашим сервером и обработки нажатия кнопки отправки.

`WebSocket` встроен в большинство современных браузеров, поэтому нам не нужно беспокоиться о подключении каких-либо библиотек. Веб-страница не будет работать в старых браузерах, но для нашего сценария это вполне допустимо.

### Как нам протестировать, что мы возвращаем правильную разметку?

Есть несколько способов. Как неоднократно подчёркивалось в этой книге, важно, чтобы ваши тесты приносили достаточно пользы, оправдывая затраты на их написание.

1. Написать тест на основе браузера, используя что-то вроде Selenium. Эти тесты наиболее «реалистичны», так как они запускают настоящий браузер и имитируют взаимодействие пользователя с ним. Такие тесты дают высокую уверенность в работе системы, но их сложнее писать, чем юнит-тесты, и они работают гораздо медленнее. Для целей нашего продукта это избыточно.
2. Сделать точное совпадение строк. Это _может_ быть приемлемо, но такие тесты оказываются очень хрупкими. Как только кто-то изменит разметку, у вас упадёт тест, хотя на практике ничего _на самом деле_ не сломалось.
3. Проверить, вызываем ли мы правильный шаблон. Мы будем использовать стандартную библиотеку шаблонов для отдачи HTML (об этом чуть позже), и мы могли бы внедрить зависимость для генерации HTML и использовать шпиона (spy) для проверки правильности её вызова. Это повлияет на дизайн нашего кода, но на самом деле мало что протестирует, кроме самого факта вызова с правильным файлом шаблона. Учитывая, что в нашем проекте будет всего один шаблон, вероятность ошибки здесь кажется низкой.

Поэтому в книге «Изучай Go с помощью тестов» мы впервые не будем писать тест.

Поместите разметку в файл под названием `game.html`.

Затем измените эндпоинт, который мы только что написали, на следующий:

```go
func (p *PlayerServer) game(w http.ResponseWriter, r *http.Request) {
	tmpl, err := template.ParseFiles("game.html")

	if err != nil {
		http.Error(w, fmt.Sprintf("problem loading template %s", err.Error()), http.StatusInternalServerError)
		return
	}

	tmpl.Execute(w, nil)
}
```

[`html/template`](https://golang.org/pkg/html/template/) — это пакет Go для создания HTML. В нашем случае мы вызываем `template.ParseFiles`, передавая путь к нашему HTML-файлу. Если ошибок нет, вы можете выполнить метод `Execute` для шаблона, который записывает данные в `io.Writer`. В нашем случае мы хотим отправить их по сети, поэтому передаем ему наш `http.ResponseWriter`.

Поскольку мы не написали тест, было бы разумно вручную протестировать наш веб-сервер, чтобы убедиться, что всё работает так, как мы ожидаем. Перейдите в каталог `cmd/webserver` и запустите файл `main.go`. Откройте в браузере страницу `http://localhost:5000/game`.

Вы _должны_ получить ошибку о том, что шаблон не найден. Вы можете либо изменить путь на относительный для вашей папки, либо скопировать `game.html` в директорию `cmd/webserver`. Я решил создать символическую ссылку (`ln -s ../../game.html game.html`) на файл в корне проекта, чтобы все изменения отражались при запуске сервера.

Если вы сделаете это изменение и запустите сервер снова, вы увидите наш пользовательский интерфейс.

Теперь нам нужно протестировать, что когда мы получаем строку через WebSocket-соединение к нашему серверу, мы объявляем её победителем игры.

## Сначала напишите тест

Мы впервые собираемся использовать внешнюю библиотеку для работы с WebSockets.

Выполните команду `go get github.com/gorilla/websocket`.

Это загрузит код отличной библиотеки [Gorilla WebSocket](https://github.com/gorilla/websocket). Теперь мы можем обновить наши тесты под новые требования.

```go
t.Run("when we get a message over a websocket it is a winner of a game", func(t *testing.T) {
	store := &StubPlayerStore{}
	winner := "Ruth"
	server := httptest.NewServer(NewPlayerServer(store))
	defer server.Close()

	wsURL := "ws" + strings.TrimPrefix(server.URL, "http") + "/ws"

	ws, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("could not open a ws connection on %s %v", wsURL, err)
	}
	defer ws.Close()

	if err := ws.WriteMessage(websocket.TextMessage, []byte(winner)); err != nil {
		t.Fatalf("could not send message over ws connection %v", err)
	}

	AssertPlayerWin(t, store, winner)
})
```

Убедитесь, что у вас импортирована библиотека `websocket`. Моя IDE сделала это автоматически, и ваша тоже должна.

Чтобы протестировать поведение со стороны браузера, нам нужно открыть собственное WebSocket-соединение и записать в него данные.

В наших предыдущих тестах сервера мы просто вызывали методы на сервере, но теперь нам нужно постоянное соединение с ним. Для этого мы используем `httptest.NewServer`, который принимает `http.Handler`, запускает его и слушает входящие подключения.

С помощью `websocket.DefaultDialer.Dial` мы пытаемся подключиться к нашему серверу, а затем пробуем отправить сообщение с именем нашего победителя `winner`.

В конце мы проверяем хранилище игроков, чтобы убедиться, что победитель был записан.

## Попробуйте запустить тест

```
=== RUN   TestGame/when_we_get_a_message_over_a_websocket_it_is_a_winner_of_a_game
    --- FAIL: TestGame/when_we_get_a_message_over_a_websocket_it_is_a_winner_of_a_game (0.00s)
        server_test.go:124: could not open a ws connection on ws://127.0.0.1:55838/ws websocket: bad handshake
```

Мы ещё не обновили наш сервер для приема WebSocket-соединений на `/ws`, так что рукопожатие (handshake) пока не происходит.

## Напишите достаточно кода, чтобы тест прошел

Добавьте ещё один маршрут в наш роутер:

```go
router.Handle("/ws", http.HandlerFunc(p.webSocket))
```

Затем добавьте наш новый обработчик `webSocket`:

```go
func (p *PlayerServer) webSocket(w http.ResponseWriter, r *http.Request) {
	upgrader := websocket.Upgrader{
		ReadBufferSize:  1024,
		WriteBufferSize: 1024,
	}
	upgrader.Upgrade(w, r, nil)
}
```

Чтобы принять соединение WebSocket, мы обновляем протокол запроса (`Upgrade`). Если вы сейчас повторно запустите тест, вы перейдете к следующей ошибке.

```
=== RUN   TestGame/when_we_get_a_message_over_a_websocket_it_is_a_winner_of_a_game
    --- FAIL: TestGame/when_we_get_a_message_over_a_websocket_it_is_a_winner_of_a_game (0.00s)
        server_test.go:132: got 0 calls to RecordWin want 1
```

Теперь, когда соединение открыто, мы хотим дождаться сообщения, а затем записать его автора как победителя.

```go
func (p *PlayerServer) webSocket(w http.ResponseWriter, r *http.Request) {
	upgrader := websocket.Upgrader{
		ReadBufferSize:  1024,
		WriteBufferSize: 1024,
	}
	conn, _ := upgrader.Upgrade(w, r, nil)
	_, winnerMsg, _ := conn.ReadMessage()
	p.store.RecordWin(string(winnerMsg))
}
```

(Да, сейчас мы игнорируем много ошибок!)

Метод `conn.ReadMessage()` блокирует выполнение в ожидании сообщения из соединения. Получив сообщение, мы используем его для вызова `RecordWin`. После этого WebSocket-соединение закрывается.

Если вы попробуете запустить тест, он всё равно упадёт.

Проблема во времени выполнения. Существует задержка между моментом, когда наше WebSocket-соединение считывает сообщение и записывает победу, и моментом завершения теста — тест завершается до того, как это произойдет. Вы можете проверить это, добавив небольшую паузу `time.Sleep` перед финальной проверкой.

Пока так и сделаем, но признаем, что добавление произвольных пауз через sleep в тесты — это **очень плохая практика**.

```go
time.Sleep(10 * time.Millisecond)
AssertPlayerWin(t, store, winner)
```

## Рефакторинг

Мы совершили много грехов, чтобы заставить этот тест работать как в коде сервера, так и в коде тестов, но помните, что для нас это самый простой способ двигаться вперед.

У нас есть грязное, ужасное, но _работающее_ приложение, покрытое тестом, так что теперь мы можем навести порядок и быть уверенными, что ничего случайно не сломаем.

Начнем с кода сервера.

Мы можем перенести `upgrader` в приватную переменную внутри нашего пакета, так как нам не нужно переобъявлять её при каждом запросе на WebSocket-соединение:

```go
var wsUpgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
}

func (p *PlayerServer) webSocket(w http.ResponseWriter, r *http.Request) {
	conn, _ := wsUpgrader.Upgrade(w, r, nil)
	_, winnerMsg, _ := conn.ReadMessage()
	p.store.RecordWin(string(winnerMsg))
}
```

Наш вызов `template.ParseFiles("game.html")` будет выполняться при каждом запросе `GET /game`. Это означает обращение к файловой системе при каждом запросе, хотя перекомпилировать шаблон нет необходимости. Давайте отрефакторим наш код так, чтобы шаблон парсился один раз в `NewPlayerServer`. Нам придется сделать так, чтобы эта функция теперь могла возвращать ошибку на случай проблем с получением шаблона с диска или его парсингом.

Вот соответствующие изменения в `PlayerServer`:

```go
type PlayerServer struct {
	store PlayerStore
	http.Handler
	template *template.Template
}

const htmlTemplatePath = "game.html"

func NewPlayerServer(store PlayerStore) (*PlayerServer, error) {
	p := new(PlayerServer)

	tmpl, err := template.ParseFiles(htmlTemplatePath)

	if err != nil {
		return nil, fmt.Errorf("problem opening %s %v", htmlTemplatePath, err)
	}

	p.template = tmpl
	p.store = store

	router := http.NewServeMux()
	router.Handle("/league", http.HandlerFunc(p.leagueHandler))
	router.Handle("/players/", http.HandlerFunc(p.playersHandler))
	router.Handle("/game", http.HandlerFunc(p.game))
	router.Handle("/ws", http.HandlerFunc(p.webSocket))

	p.Handler = router

	return p, nil
}

func (p *PlayerServer) game(w http.ResponseWriter, r *http.Request) {
	p.template.Execute(w, nil)
}
```

Изменив сигнатуру `NewPlayerServer`, мы получили проблемы с компиляцией. Попробуйте исправить их самостоятельно или обратитесь к исходному коду, если возникнут трудности.

Для тестового кода я создал вспомогательную функцию `mustMakePlayerServer(t *testing.T, store PlayerStore) *PlayerServer`, чтобы скрыть шум обработки ошибок из тестов.

```go
func mustMakePlayerServer(t *testing.T, store PlayerStore) *PlayerServer {
	server, err := NewPlayerServer(store)
	if err != nil {
		t.Fatal("problem creating player server", err)
	}
	return server
}
```

Аналогично я создал другой хелпер `mustDialWS`, чтобы скрыть неприятный шум обработки ошибок при создании WebSocket-соединения.

```go
func mustDialWS(t *testing.T, url string) *websocket.Conn {
	ws, _, err := websocket.DefaultDialer.Dial(url, nil)

	if err != nil {
		t.Fatalf("could not open a ws connection on %s %v", url, err)
	}

	return ws
}
```

И наконец, в нашем тестовом коде мы можем создать хелпер, чтобы упростить отправку сообщений:

```go
func writeWSMessage(t testing.TB, conn *websocket.Conn, message string) {
	t.Helper()
	if err := conn.WriteMessage(websocket.TextMessage, []byte(message)); err != nil {
		t.Fatalf("could not send message over ws connection %v", err)
	}
}
```

Теперь, когда тесты проходят, попробуйте запустить сервер и объявить нескольких победителей на `/game`. Вы должны увидеть, что они записываются на странице `/league`. Помните, что каждый раз, когда мы получаем победителя, мы _закрываем соединение_, так что вам нужно будет обновить страницу, чтобы открыть соединение снова.

Мы создали простейшую веб-форму, которая позволяет пользователям записывать победителя игры. Давайте доработаем её, чтобы пользователь мог начать игру, указав количество игроков, а сервер отправлял клиенту push-сообщения со значением блайнда по прошествии времени.

Сначала обновите `game.html`, чтобы адаптировать наш клиентский код под новые требования:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Lets play poker</title>
</head>
<body>
<section id="game">
    <div id="game-start">
        <label for="player-count">Number of players</label>
        <input type="number" id="player-count"/>
        <button id="start-game">Start</button>
    </div>

    <div id="declare-winner">
        <label for="winner">Winner</label>
        <input type="text" id="winner"/>
        <button id="winner-button">Declare winner</button>
    </div>

    <div id="blind-value"/>
</section>

<section id="game-end">
    <h1>Another great game of poker everyone!</h1>
    <p><a href="/league">Go check the league table</a></p>
</section>

</body>
<script type="application/javascript">
    const startGame = document.getElementById('game-start')

    const declareWinner = document.getElementById('declare-winner')
    const submitWinnerButton = document.getElementById('winner-button')
    const winnerInput = document.getElementById('winner')

    const blindContainer = document.getElementById('blind-value')

    const gameContainer = document.getElementById('game')
    const gameEndContainer = document.getElementById('game-end')

    declareWinner.hidden = true
    gameEndContainer.hidden = true

    document.getElementById('start-game').addEventListener('click', event => {
        startGame.hidden = true
        declareWinner.hidden = false

        const numberOfPlayers = document.getElementById('player-count').value

        if (window['WebSocket']) {
            const conn = new WebSocket('ws://' + document.location.host + '/ws')

            submitWinnerButton.onclick = event => {
                conn.send(winnerInput.value)
                gameEndContainer.hidden = false
                gameContainer.hidden = true
            }

            conn.onclose = evt => {
                blindContainer.innerText = 'Connection closed'
            }

            conn.onmessage = evt => {
                blindContainer.innerText = evt.data
            }

            conn.onopen = function () {
                conn.send(numberOfPlayers)
            }
        }
    })
</script>
</html>
```

Основные изменения — добавление раздела для ввода количества игроков и раздела для отображения значения блайнда. У нас есть немного логики для показа/скрытия пользовательского интерфейса в зависимости от стадии игры.

Любое сообщение, полученное через `conn.onmessage`, мы считаем оповещением о блайнде, поэтому соответствующим образом устанавливаем `blindContainer.innerText`.

Как нам отправлять оповещения о блайндах? В предыдущей главе мы ввели концепцию `Game`, чтобы наш CLI-код мог вызывать `Game`, а всё остальное, включая планирование оповещений о блайндах, брало на себя само приложение. Это оказалось хорошим разделением обязанностей.

```go
type Game interface {
	Start(numberOfPlayers int)
	Finish(winner string)
}
```

Когда в CLI пользователю предлагалось ввести количество игроков, приложение вызывало `Start` для запуска игры, что запускало оповещения о блайндах, а когда пользователь объявлял победителя, вызывался метод `Finish`. Это те же самые требования, что и сейчас, просто способ получения входных данных отличается. Поэтому нам следует попытаться повторно использовать эту концепцию.

Наша «реальная» реализация `Game` — это `TexasHoldem`:

```go
type TexasHoldem struct {
	alerter BlindAlerter
	store   PlayerStore
}
```

Передавая `BlindAlerter`, структура `TexasHoldem` может планировать отправку оповещений о блайндах _куда угодно_:

```go
type BlindAlerter interface {
	ScheduleAlertAt(duration time.Duration, amount int)
}
```

И в качестве напоминания — вот наша реализация `BlindAlerter`, которую мы используем в CLI:

```go
func StdOutAlerter(duration time.Duration, amount int) {
	time.AfterFunc(duration, func() {
		fmt.Fprintf(os.Stdout, "Blind is now %d\n", amount)
	})
}
```

Это работает в CLI, потому что мы _всегда хотим выводить оповещения в `os.Stdout`_, но это не сработает для нашего веб-сервера. При каждом запросе мы получаем новый `http.ResponseWriter`, который затем преобразуем в `*websocket.Conn`. Таким образом, во время конструирования наших зависимостей мы не можем знать, куда должны отправляться оповещения.

По этой причине нам нужно изменить `BlindAlerter.ScheduleAlertAt` так, чтобы метод принимал место назначения для оповещений. Тогда мы сможем повторно использовать его на нашем веб-сервере.

Откройте `blind_alerter.go` и добавьте параметр типа `io.Writer`:

```go
type BlindAlerter interface {
	ScheduleAlertAt(duration time.Duration, amount int, to io.Writer)
}

type BlindAlerterFunc func(duration time.Duration, amount int, to io.Writer)

func (a BlindAlerterFunc) ScheduleAlertAt(duration time.Duration, amount int, to io.Writer) {
	a(duration, amount, to)
}
```

Идея `StdoutAlerter` больше не укладывается в нашу новую модель, поэтому просто переименуйте его в `Alerter`:

```go
func Alerter(duration time.Duration, amount int, to io.Writer) {
	time.AfterFunc(duration, func() {
		fmt.Fprintf(to, "Blind is now %d\n", amount)
	})
}
```

Если вы попробуете скомпилировать код, возникнет ошибка в `TexasHoldem`, так как он вызывает `ScheduleAlertAt` без указания места назначения. Чтобы код снова компилировался, _пока что_ жестко пропишите там `os.Stdout`.

Попробуйте запустить тесты, и они упадут, потому что `SpyBlindAlerter` больше не реализует `BlindAlerter`. Исправьте это, обновив сигнатуру `ScheduleAlertAt`, запустите тесты, и мы снова должны увидеть зеленый статус.

Для `TexasHoldem` нет никакого смысла знать, куда отправлять оповещения о блайндах. Давайте теперь обновим `Game` так, чтобы при запуске игры вы указывали, _куда_ должны идти оповещения.

```go
type Game interface {
	Start(numberOfPlayers int, alertsDestination io.Writer)
	Finish(winner string)
}
```

Пусть компилятор подскажет вам, что нужно исправить. Изменения не так уж страшны:

* Обновите `TexasHoldem`, чтобы структура правильно реализовывала интерфейс `Game`.
* В структуре `CLI` при запуске игры передайте наше свойство `out` (`cli.game.Start(numberOfPlayers, cli.out)`).
* В тестах `TexasHoldem` используйте `game.Start(5, io.Discard)`, чтобы исправить проблему с компиляцией и перенаправить вывод оповещений в никуда (discard).

Если вы все сделали правильно, все тесты должны стать зелеными! Теперь мы можем попробовать использовать интерфейс `Game` внутри нашего `Server`.

## Сначала напишите тест

Требования к `CLI` и `Server` одинаковы! Различается только механизм доставки.

Давайте взглянем на наш тест `CLI` для вдохновения.

```go
t.Run("start game with 3 players and finish game with 'Chris' as winner", func(t *testing.T) {
	game := &GameSpy{}

	out := &bytes.Buffer{}
	in := userSends("3", "Chris wins")

	poker.NewCLI(in, out, game).PlayPoker()

	assertMessagesSentToUser(t, out, poker.PlayerPrompt)
	assertGameStartedWith(t, game, 3)
	assertFinishCalledWith(t, game, "Chris")
})
```

Похоже, мы сможем разработать через тестирование (test drive) аналогичный результат, используя `GameSpy`.

Замените старый WebSocket-тест следующим:

```go
t.Run("start a game with 3 players and declare Ruth the winner", func(t *testing.T) {
	game := &poker.GameSpy{}
	winner := "Ruth"
	server := httptest.NewServer(mustMakePlayerServer(t, dummyPlayerStore, game))
	ws := mustDialWS(t, "ws"+strings.TrimPrefix(server.URL, "http")+"/ws")

	defer server.Close()
	defer ws.Close()

	writeWSMessage(t, ws, "3")
	writeWSMessage(t, ws, winner)

	time.Sleep(10 * time.Millisecond)
	assertGameStartedWith(t, game, 3)
	assertFinishCalledWith(t, game, winner)
})
```

* Как и обсуждалось, мы создаем шпион (spy) `Game` и передаем его в хелпер `mustMakePlayerServer` (не забудьте обновить хелпер для его поддержки).
* Затем мы отправляем сообщения через веб-сокет для игры.
* Наконец, мы проверяем, что игра началась и завершилась с ожидаемыми значениями.

## Попробуйте запустить тест

У вас возникнет ряд ошибок компиляции вокруг `mustMakePlayerServer` в других тестах. Объявите неэкспортируемую переменную `dummyGame` и используйте её во всех некомпилирующихся тестах:

```go
var (
	dummyGame = &GameSpy{}
)
```

Финальная ошибка возникнет там, где мы пытаемся передать `Game` в `NewPlayerServer`, но он её пока не поддерживает:

```
./server_test.go:21:38: too many arguments in call to "github.com/quii/learn-go-with-tests/WebSockets/v2".NewPlayerServer
	have ("github.com/quii/learn-go-with-tests/WebSockets/v2".PlayerStore, "github.com/quii/learn-go-with-tests/WebSockets/v2".Game)
	want ("github.com/quii/learn-go-with-tests/WebSockets/v2".PlayerStore)
```

## Напишите минимальное количество кода, чтобы запустить тест и проверить вывод упавшего теста

Пока просто добавьте её в качестве аргумента, чтобы запустить тест:

```go
func NewPlayerServer(store PlayerStore, game Game) (*PlayerServer, error)
```

Наконец-то!

```
=== RUN   TestGame/start_a_game_with_3_players_and_declare_Ruth_the_winner
--- FAIL: TestGame (0.01s)
    --- FAIL: TestGame/start_a_game_with_3_players_and_declare_Ruth_the_winner (0.01s)
    	server_test.go:146: wanted Start called with 3 but got 0
    	server_test.go:147: expected finish called with 'Ruth' but got ''
FAIL
```

## Напишите достаточно кода, чтобы тест прошел

Нам нужно добавить поле `Game` в `PlayerServer`, чтобы сервер мог использовать его при получении запросов.

```go
type PlayerServer struct {
	store PlayerStore
	http.Handler
	template *template.Template
	game     Game
}
```

(У нас уже есть метод с именем `game`, поэтому переименуйте его в `playGame`)

Далее давайте присвоим её в нашем конструкторе:

```go
func NewPlayerServer(store PlayerStore, game Game) (*PlayerServer, error) {
	p := new(PlayerServer)

	tmpl, err := template.ParseFiles(htmlTemplatePath)

	if err != nil {
		return nil, fmt.Errorf("problem opening %s %v", htmlTemplatePath, err)
	}

	p.game = game

	// etc
}
```

Теперь мы можем использовать `Game` внутри метода `webSocket`.

```go
func (p *PlayerServer) webSocket(w http.ResponseWriter, r *http.Request) {
	conn, _ := wsUpgrader.Upgrade(w, r, nil)

	_, numberOfPlayersMsg, _ := conn.ReadMessage()
	numberOfPlayers, _ := strconv.Atoi(string(numberOfPlayersMsg))
	p.game.Start(numberOfPlayers, io.Discard) //todo: Don't discard the blinds messages!

	_, winner, _ := conn.ReadMessage()
	p.game.Finish(string(winner))
}
```

Ура! Тесты проходят.

Мы _пока что_ не будем отправлять сообщения о блайндах куда-либо, так как нам нужно подумать над этим. При вызове `game.Start` мы передаем `io.Discard`, который просто отбрасывает любые записанные в него сообщения.

А пока запустите веб-сервер. Вам потребуется обновить `main.go`, чтобы передавать `Game` в `PlayerServer`:

```go
func main() {
	db, err := os.OpenFile(dbFileName, os.O_RDWR|os.O_CREATE, 0666)

	if err != nil {
		log.Fatalf("problem opening %s %v", dbFileName, err)
	}

	store, err := poker.NewFileSystemPlayerStore(db)

	if err != nil {
		log.Fatalf("problem creating file system player store, %v ", err)
	}

	game := poker.NewTexasHoldem(poker.BlindAlerterFunc(poker.Alerter), store)

	server, err := poker.NewPlayerServer(store, game)

	if err != nil {
		log.Fatalf("problem creating player server %v", err)
	}

	log.Fatal(http.ListenAndServe(":5000", server))
}
```

Даже без учета того, что мы пока не получаем оповещения о блайндах, приложение работает! Нам удалось повторно использовать `Game` в `PlayerServer`, и он взял на себя все детали. Как только мы разберемся, как отправлять наши оповещения о блайндах в веб-сокеты вместо того, чтобы отбрасывать их, всё _должно_ заработать.

Прежде чем сделать это, давайте наведем порядок в коде.

## Рефакторинг

То, как мы используем WebSockets, довольно примитивно, а обработка ошибок наивна, поэтому я захотел инкапсулировать это в отдельный тип, чтобы избавить код сервера от этой путаницы. Возможно, мы вернемся к этому позже, но пока это немного наведёт порядок:

```go
type playerServerWS struct {
	*websocket.Conn
}

func newPlayerServerWS(w http.ResponseWriter, r *http.Request) *playerServerWS {
	conn, err := wsUpgrader.Upgrade(w, r, nil)

	if err != nil {
		log.Printf("problem upgrading connection to WebSockets %v\n", err)
	}

	return &playerServerWS{conn}
}

func (w *playerServerWS) WaitForMsg() string {
	_, msg, err := w.ReadMessage()
	if err != nil {
		log.Printf("error reading from websocket %v\n", err)
	}
	return string(msg)
}
```

Теперь код сервера стал немного проще:

```go
func (p *PlayerServer) webSocket(w http.ResponseWriter, r *http.Request) {
	ws := newPlayerServerWS(w, r)

	numberOfPlayersMsg := ws.WaitForMsg()
	numberOfPlayers, _ := strconv.Atoi(numberOfPlayersMsg)
	p.game.Start(numberOfPlayers, ws) //todo: Don't discard the blinds messages!

	winner := ws.WaitForMsg()
	p.game.Finish(winner)
}
```

Как только мы разберемся, как не отбрасывать сообщения о блайндах, дело будет сделано.

### Давайте _не будем_ писать тест!

Иногда, когда мы не уверены, как что-то сделать, лучше всего просто поиграть с кодом и поэкспериментировать! Сначала убедитесь, что ваша работа закоммичена, потому что как только мы найдем решение, нам нужно будет реализовать его через тест.

Проблемная строка кода, которая у нас есть:

```go
p.game.Start(numberOfPlayers, io.Discard) //todo: Don't discard the blinds messages!
```

Нам нужно передать `io.Writer`, чтобы игра могла записывать в него оповещения о блайндах.

Было бы здорово, если бы мы могли передать наш `playerServerWS`, созданный ранее? Это наша обёртка вокруг WebSocket, так что _кажется_, что мы должны иметь возможность передать её в `Game` для отправки сообщений.

Попробуйте сделать это:

```go
func (p *PlayerServer) webSocket(w http.ResponseWriter, r *http.Request) {
	ws := newPlayerServerWS(w, r)

	numberOfPlayersMsg := ws.WaitForMsg()
	numberOfPlayers, _ := strconv.Atoi(numberOfPlayersMsg)
	p.game.Start(numberOfPlayers, ws)
	//etc...
}
```

Компилятор ругается:

```
./server.go:71:14: cannot use ws (type *playerServerWS) as type io.Writer in argument to p.game.Start:
	*playerServerWS does not implement io.Writer (missing Write method)
```

Очевидное решение — сделать так, чтобы `playerServerWS` _действительно_ реализовывал интерфейс `io.Writer`. Для этого мы воспользуемся базовым `*websocket.Conn`, чтобы вызывать `WriteMessage` и отправлять сообщение в веб-сокет:

```go
func (w *playerServerWS) Write(p []byte) (n int, err error) {
	err = w.WriteMessage(websocket.TextMessage, p)

	if err != nil {
		return 0, err
	}

	return len(p), nil
}
```

Это кажется слишком простым! Попробуйте запустить приложение и посмотрите, работает ли оно.

Перед этим отредактируйте `TexasHoldem`, чтобы время увеличения блайнда было короче, и вы могли увидеть его в действии:

```go
blindIncrement := time.Duration(5+numberOfPlayers) * time.Second // (rather than a minute)
```

Вы должны увидеть, что всё работает! Значение блайнда увеличивается в браузере как по волшебству.

Теперь давайте откатим изменения и подумаем, как это протестировать. Чтобы _реализовать_ это, всё, что мы сделали, — передали в `StartGame` структуру `playerServerWS` вместо `io.Discard`, так что вы можете подумать, что нам стоит сделать шпиона (spy) для этого вызова, чтобы проверить его работу.

Тесты со шпионами (spies) — это здорово, они помогают проверять детали реализации. Однако по возможности мы всегда должны отдавать предпочтение тестированию _реального_ поведения. Когда вы решите провести рефакторинг, часто именно тесты со шпионами начинают ломаться, потому что они обычно проверяют детали реализации, которые вы как раз пытаетесь изменить.

Наш тест в данный момент открывает WebSocket-соединение с работающим сервером и отправляет сообщения, чтобы заставить его выполнять действия. Точно так же мы должны иметь возможность тестировать сообщения, которые наш сервер отправляет обратно через WebSocket-соединение.

## Сначала напишите тест

Мы отредактируем наш существующий тест.

В настоящее время наш `GameSpy` не отправляет никаких данных в `out` при вызове `Start`. Нам нужно изменить его так, чтобы мы могли настроить его на отправку заготовленного сообщения, а затем проверить, что это сообщение отправляется в веб-сокет. Это должно дать нам уверенность в том, что мы всё настроили правильно, при этом по-прежнему проверяя реальное поведение.

```go
type GameSpy struct {
	StartCalled     bool
	StartCalledWith int
	BlindAlert      []byte

	FinishedCalled   bool
	FinishCalledWith string
}
```

Добавьте поле `BlindAlert`.

Обновите метод `Start` в `GameSpy`, чтобы он отправлял заготовленное сообщение в `out`.

```go
func (g *GameSpy) Start(numberOfPlayers int, out io.Writer) {
	g.StartCalled = true
	g.StartCalledWith = numberOfPlayers
	out.Write(g.BlindAlert)
}
```

Это означает, что когда мы тестируем `PlayerServer` и он пытается вызвать `Start` для запуска игры, в итоге должны отправляться сообщения через веб-сокет, если всё работает правильно.

Наконец, мы можем обновить тест:

```go
t.Run("start a game with 3 players, send some blind alerts down WS and declare Ruth the winner", func(t *testing.T) {
	wantedBlindAlert := "Blind is 100"
	winner := "Ruth"

	game := &GameSpy{BlindAlert: []byte(wantedBlindAlert)}
	server := httptest.NewServer(mustMakePlayerServer(t, dummyPlayerStore, game))
	ws := mustDialWS(t, "ws"+strings.TrimPrefix(server.URL, "http")+"/ws")

	defer server.Close()
	defer ws.Close()

	writeWSMessage(t, ws, "3")
	writeWSMessage(t, ws, winner)

	time.Sleep(10 * time.Millisecond)
	assertGameStartedWith(t, game, 3)
	assertFinishCalledWith(t, game, winner)

	_, gotBlindAlert, _ := ws.ReadMessage()

	if string(gotBlindAlert) != wantedBlindAlert {
		t.Errorf("got blind alert %q, want %q", string(gotBlindAlert), wantedBlindAlert)
	}
})
```

* Мы добавили переменную `wantedBlindAlert` и настроили наш `GameSpy` на отправку этого сообщения в `out`, если вызывается `Start`.
* Мы ожидаем, что оно будет отправлено в WebSocket-соединение, поэтому мы добавили вызов `ws.ReadMessage()`, чтобы дождаться отправки сообщения и проверить, совпадает ли оно с ожидаемым.

## Попробуйте запустить тест

Вы обнаружите, что тест зависает навсегда. Это происходит потому, что `ws.ReadMessage()` будет заблокирован до тех пор, пока не получит сообщение, чего никогда не случится.

## Напишите минимальное количество кода, чтобы запустить тест и проверить вывод упавшего теста

У нас никогда не должно быть зависающих тестов, поэтому давайте реализуем способ обработки кода, для которого мы хотим задать таймаут.

```go
func within(t testing.TB, d time.Duration, assert func()) {
	t.Helper()

	done := make(chan struct{}, 1)

	go func() {
		assert()
		done <- struct{}{}
	}()

	select {
	case <-time.After(d):
		t.Error("timed out")
	case <-done:
	}
}
```

Функция `within` принимает функцию `assert` в качестве аргумента, а затем запускает её в горутине. Когда функция завершает работу, она сигнализирует об этом через канал `done`.

Пока это происходит, мы используем оператор `select`, который позволяет нам ожидать отправки сообщения из канала. Здесь возникает состояние гонки между функцией `assert` и `time.After`, которая отправит сигнал по истечении заданного времени.

Наконец, я создал вспомогательную функцию для нашего утверждения (assertion), просто чтобы сделать код немного аккуратнее:

```go
func assertWebsocketGotMsg(t *testing.T, ws *websocket.Conn, want string) {
	_, msg, _ := ws.ReadMessage()
	if string(msg) != want {
		t.Errorf(`got "%s", want "%s"`, string(msg), want)
	}
}
```

Вот как теперь выглядит этот тест:

```go
t.Run("start a game with 3 players, send some blind alerts down WS and declare Ruth the winner", func(t *testing.T) {
	wantedBlindAlert := "Blind is 100"
	winner := "Ruth"

	game := &GameSpy{BlindAlert: []byte(wantedBlindAlert)}
	server := httptest.NewServer(mustMakePlayerServer(t, dummyPlayerStore, game))
	ws := mustDialWS(t, "ws"+strings.TrimPrefix(server.URL, "http")+"/ws")

	defer server.Close()
	defer ws.Close()

	writeWSMessage(t, ws, "3")
	writeWSMessage(t, ws, winner)

	time.Sleep(tenMS)

	assertGameStartedWith(t, game, 3)
	assertFinishCalledWith(t, game, winner)
	within(t, tenMS, func() { assertWebsocketGotMsg(t, ws, wantedBlindAlert) })
})
```

Теперь, если вы запустите тест...

```
=== RUN   TestGame
=== RUN   TestGame/start_a_game_with_3_players,_send_some_blind_alerts_down_WS_and_declare_Ruth_the_winner
--- FAIL: TestGame (0.02s)
    --- FAIL: TestGame/start_a_game_with_3_players,_send_some_blind_alerts_down_WS_and_declare_Ruth_the_winner (0.02s)
    	server_test.go:143: timed out
    	server_test.go:150: got "", want "Blind is 100"
```

## Напишите достаточно кода, чтобы тест прошел

Наконец-то мы можем изменить код нашего сервера, чтобы он передавал наше WebSocket-соединение в игру при её запуске:

```go
func (p *PlayerServer) webSocket(w http.ResponseWriter, r *http.Request) {
	ws := newPlayerServerWS(w, r)

	numberOfPlayersMsg := ws.WaitForMsg()
	numberOfPlayers, _ := strconv.Atoi(numberOfPlayersMsg)
	p.game.Start(numberOfPlayers, ws)

	winner := ws.WaitForMsg()
	p.game.Finish(winner)
}
```

## Рефакторинг

Изменения в коде сервера были совсем небольшими, так что здесь особо нечего менять, но в тестовом коде всё ещё присутствует вызов `time.Sleep`, потому что нам приходится ждать, пока наш сервер выполнит свою работу асинхронно.

Мы можем отрефакторить наши хелперы `assertGameStartedWith` and `assertFinishCalledWith` так, чтобы они могли повторно запускать проверки в течение короткого периода времени перед тем, как упасть с ошибкой.

Вот как вы можете сделать это для `assertFinishCalledWith` (тот же подход можно использовать и для другого хелпера):

```go
func assertFinishCalledWith(t testing.TB, game *GameSpy, winner string) {
	t.Helper()

	passed := retryUntil(500*time.Millisecond, func() bool {
		return game.FinishCalledWith == winner
	})

	if !passed {
		t.Errorf("expected finish called with %q but got %q", winner, game.FinishCalledWith)
	}
}
```

Вот как определяется функция `retryUntil`:

```go
func retryUntil(d time.Duration, f func() bool) bool {
	deadline := time.Now().Add(d)
	for time.Now().Before(deadline) {
		if f() {
			return true
		}
	}
	return false
}
```

## Итоги

Наше приложение теперь полностью готово. Игра в покер может быть запущена через веб-браузер, а пользователи информируются о текущем значении блайнда по прошествии времени через WebSockets. Когда игра заканчивается, они могут записать победителя, который сохраняется с помощью кода, написанного нами несколько глав назад. Игроки могут узнать, кто лучший (или самый везучий) игрок в покер, используя эндпоинт `/league` нашего веб-сайта.

На этом пути мы совершали ошибки, но благодаря подходу TDD мы никогда не отдалялись слишком сильно от работающего ПО. Мы могли свободно продолжать итерации и эксперименты.

Финальная глава будет посвящена ретроспективе этого подхода, дизайну, к которому мы пришли, и подведению итогов.

В этой главе мы рассмотрели несколько вещей:

### WebSockets

* Удобный способ отправки сообщений между клиентами и серверами, не требующий от клиента постоянного опроса сервера. Код как клиента, так и сервера у нас получился очень простым.
* Их тривиально тестировать, но нужно быть осторожными с асинхронной природой тестов.

### Обработка в тестах кода, который может выполняться с задержкой или никогда не завершиться

* Создание вспомогательных функций для повторных проверок (assertions) и добавления таймаутов.
* Мы можем использовать горутины, чтобы проверки не блокировали поток выполнения, а затем использовать каналы, чтобы они могли сигнализировать о своем завершении (или его отсутствии).
* В пакете `time` есть полезные функции, которые также отправляют сигналы через каналы о событиях во времени, благодаря чему мы можем устанавливать таймауты.