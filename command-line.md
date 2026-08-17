# Командная строка и структура проекта

**[Весь код для этой главы вы найдете здесь](https://github.com/quii/learn-go-with-tests/tree/main/command-line)**

Наш продукт-оунер теперь хочет _изменить направление_, представив второе приложение — приложение командной строки.

Пока оно должно будет просто записывать победу игрока, когда пользователь вводит `Ruth wins`. Предполагается, что в конечном итоге это будет инструмент для помощи пользователям в игре в покер.

Продукт-оунер хочет, чтобы база данных была общей для двух приложений, так чтобы лига обновлялась в соответствии с победами, записанными в новом приложении.

## Напоминание о коде

У нас есть приложение с файлом `main.go`, который запускает HTTP-сервер. HTTP-сервер не будет интересен нам для этого упражнения, но абстракция, которую он использует, будет. Он зависит от `PlayerStore`.

```go
type PlayerStore interface {
	GetPlayerScore(name string) int
	RecordWin(name string)
	GetLeague() League
}
```

В предыдущей главе мы создали `FileSystemPlayerStore`, который реализует этот интерфейс. Мы должны иметь возможность повторно использовать часть этого для нашего нового приложения.

## Сначала немного рефакторинга проекта

Нашему проекту теперь необходимо создать два бинарника: существующий веб-сервер и приложение командной строки.

Прежде чем мы приступим к новой работе, нам следует структурировать наш проект, чтобы это учесть.

До сих пор весь код хранился в одной папке, по пути, выглядящему так:

`$GOPATH/src/github.com/your-name/my-app`

Чтобы создать приложение на Go, вам нужна функция `main` внутри `package main`. До сих пор весь наш "доменный" код жил внутри `package main`, и наша `func main` могла ссылаться на всё.

Это было нормально до сих пор, и хорошей практикой является не переусердствовать со структурой пакетов. Если вы потратите время на просмотр стандартной библиотеки, вы увидите очень мало большого количества папок и структуры.

К счастью, добавить структуру довольно просто, _когда она вам нужна_.

Внутри существующего проекта создайте каталог `cmd` с каталогом `webserver` внутри него (например, `mkdir -p cmd/webserver`).

`cmd` — это широко используемая в Go конвенция для хранения `main` пакетов приложений, которые собирает проект, отделяя их от импортируемого библиотечного кода, который находится в корне проекта.

Переместите `main.go` туда.

Если у вас установлен `tree`, запустите его, и ваша структура должна выглядеть так:

```
.
|-- file_system_store.go
|-- file_system_store_test.go
|-- cmd
|   |-- webserver
|       |-- main.go
|-- league.go
|-- server.go
|-- server_integration_test.go
|-- server_test.go
|-- tape.go
|-- tape_test.go
```

Теперь у нас фактически есть разделение между нашим приложением и библиотечным кодом, но теперь нам нужно изменить некоторые имена пакетов. Помните, что при сборке приложения Go его пакет _должен_ быть `main`.

Измените весь остальной код, чтобы он имел пакет с именем `poker`.

Наконец, нам нужно импортировать этот пакет в `main.go`, чтобы мы могли использовать его для создания нашего веб-сервера. Тогда мы сможем использовать наш библиотечный код, используя `poker.FunctionName`.

Пути на вашем компьютере будут отличаться, но должно быть что-то похожее на это:

```go
// cmd/webserver/main.go
package main

import (
	"github.com/quii/learn-go-with-tests/command-line/v1"
	"log"
	"net/http"
	"os"
)

const dbFileName = "game.db.json"

func main() {
	db, err := os.OpenFile(dbFileName, os.O_RDWR|os.O_CREATE, 0666)

	if err != nil {
		log.Fatalf("problem opening %s %v", dbFileName, err)
	}

	store, err := poker.NewFileSystemPlayerStore(db)

	if err != nil {
		log.Fatalf("problem creating file system player store, %v ", err)
	}

	server := poker.NewPlayerServer(store)

	log.Fatal(http.ListenAndServe(":5000", server))
}
```

`dbFileName` — это относительный путь, поэтому `game.db.json` будет создан (или прочитан) относительно того каталога, _из которого_ вы запускаете полученный бинарник, а не каталога, в котором находится бинарник. Поскольку наш продукт-оунер хочет, чтобы CLI и веб-сервер использовали одну и ту же базу данных, это важно: запуск обоих из разных каталогов молча предоставит каждому из них свой собственный, отдельный `game.db.json`. Мы вернемся к этому в разделе "Финальные проверки" ниже.

Полный путь может показаться немного странным, но именно так вы можете импортировать _любую_ общедоступную библиотеку в свой код.

Разделив наш доменный код на отдельный пакет и опубликовав его в публичном репозитории, таком как GitHub, любой Go-разработчик может написать свой собственный код, который импортирует этот пакет, делая доступными написанные нами функции. При первом запуске он будет жаловаться, что его не существует, но все, что вам нужно сделать, это выполнить `go get`.

Кроме того, пользователи могут просмотреть [документацию на pkg.go.dev](https://pkg.go.dev/github.com/quii/learn-go-with-tests/command-line/v1).

### Финальные проверки

-   В корневом каталоге запустите `go test` и убедитесь, что тесты все еще проходят.
-   Перейдите в `cmd/webserver` и выполните `go run main.go`.
    -   Посетите `http://localhost:5000/league`, и вы должны увидеть, что все еще работает.

Позже в этой главе мы создадим второе приложение, `cmd/cli`, которое должно использовать тот же `game.db.json`, что и веб-сервер. Поскольку `dbFileName` разрешается относительно текущего рабочего каталога, вам нужно будет запускать оба бинарника _из одного и того же каталога_, чтобы они видели обновления друг друга, например, сначала собрав их и запустив бинарники из корня проекта (`go build -o webserver ./cmd/webserver && go build -o cli ./cmd/cli`, затем `./webserver` и `./cli`), а не используя `go run main.go` из каждой подпапки `cmd`.

### Рабочий скелет

Прежде чем мы приступим к написанию тестов, давайте добавим новое приложение, которое будет собирать наш проект. Создайте еще один каталог внутри `cmd` под названием `cli` (command line interface) и добавьте `main.go` со следующим содержимым:

```go
// cmd/cli/main.go
package main

import "fmt"

func main() {
	fmt.Println("Let's play poker")
}
```

Первое требование, с которым мы справимся, — это запись победы, когда пользователь вводит `{PlayerName} wins`.

## Сначала напишите тест

Мы знаем, что нам нужно создать нечто под названием `CLI`, которое позволит нам `Play` в покер. Оно должно будет читать ввод пользователя, а затем записывать победы в `PlayerStore`.

Однако, прежде чем заходить слишком далеко, давайте просто напишем тест, чтобы убедиться, что он интегрируется с `PlayerStore` так, как мы хотим.

Внутри `CLI_test.go` (в корне проекта, не внутри `cmd`)

```go
// CLI_test.go
package poker

import "testing"

func TestCLI(t *testing.T) {
	playerStore := &StubPlayerStore{}
	cli := &CLI{playerStore}
	cli.PlayPoker()

	if len(playerStore.winCalls) != 1 {
		t.Fatal("expected a win call but didn't get any")
	}
}
```

-   Мы можем использовать наш `StubPlayerStore` из других тестов.
-   Мы передаем нашу зависимость в еще не существующий тип `CLI`.
-   Запускаем игру с помощью ненаписанного метода `PlayPoker`.
-   Проверяем, что победа записана.

## Попробуйте запустить тест

```
# github.com/quii/learn-go-with-tests/command-line/v2
./cli_test.go:25:10: undefined: CLI
```

## Напишите минимальное количество кода, чтобы тест запустился и проверьте вывод ошибочного теста

На этом этапе вы должны быть достаточно уверенными, чтобы создать нашу новую структуру `CLI` с соответствующим полем для нашей зависимости и добавить метод.

В итоге у вас должен получиться такой код:

```go
// CLI.go
package poker

type CLI struct {
	playerStore PlayerStore
}

func (cli *CLI) PlayPoker() {}
```

Помните, что мы просто пытаемся запустить тест, чтобы убедиться, что он завершается ошибкой, как мы и ожидали:

```
--- FAIL: TestCLI (0.00s)
    cli_test.go:30: expected a win call but didn't get any
FAIL
```

## Напишите достаточно кода, чтобы он прошел

```go
//CLI.go
func (cli *CLI) PlayPoker() {
	cli.playerStore.RecordWin("Cleo")
}
```

Это должно заставить его пройти.

Далее нам нужно симулировать чтение из `Stdin` (ввод от пользователя), чтобы мы могли записывать победы для конкретных игроков.

Давайте расширим наш тест, чтобы проверить это.

## Сначала напишите тест

```go
//CLI_test.go
func TestCLI(t *testing.T) {
	in := strings.NewReader("Chris wins\n")
	playerStore := &StubPlayerStore{}

	cli := &CLI{playerStore, in}
	cli.PlayPoker()

	if len(playerStore.winCalls) != 1 {
		t.Fatal("expected a win call but didn't get any")
	}

	got := playerStore.winCalls[0]
	want := "Chris"

	if got != want {
		t.Errorf("didn't record correct winner, got %q, want %q", got, want)
	}
}
```

`os.Stdin` — это то, что мы будем использовать в `main` для захвата ввода пользователя. По сути, это `*File`, что означает, что он реализует `io.Reader`, который, как мы теперь знаем, является удобным способом захвата текста.

Мы создаем `io.Reader` в нашем тесте, используя удобный `strings.NewReader`, заполняя его тем, что, как мы ожидаем, введет пользователь.

## Попробуйте запустить тест

`./CLI_test.go:12:32: too many values in struct initializer`

## Напишите минимальное количество кода, чтобы тест запустился и проверьте вывод ошибочного теста

Нам нужно добавить нашу новую зависимость в `CLI`.

```go
//CLI.go
type CLI struct {
	playerStore PlayerStore
	in          io.Reader
}
```

```
--- FAIL: TestCLI (0.00s)
    CLI_test.go:23: didn't record the correct winner, got 'Cleo', want 'Chris'
FAIL
```

## Напишите достаточно кода, чтобы он прошел

Помните, что сначала нужно сделать строго самое простое:

```go
func (cli *CLI) PlayPoker() {
	cli.playerStore.RecordWin("Chris")
}
```

Тест проходит. Далее мы добавим еще один тест, чтобы заставить себя написать настоящий код, но сначала давайте проведем рефакторинг.

## Рефакторинг

В `server_test` мы ранее делали проверки, чтобы увидеть, записываются ли победы, как здесь. Давайте устраним это дублирование утверждения в вспомогательной функции:

```go
//server_test.go
func assertPlayerWin(t testing.TB, store *StubPlayerStore, winner string) {
	t.Helper()

	if len(store.winCalls) != 1 {
		t.Fatalf("got %d calls to RecordWin want %d", len(store.winCalls), 1)
	}

	if store.winCalls[0] != winner {
		t.Errorf("did not store correct winner got %q want %q", store.winCalls[0], winner)
	}
}
```

Теперь замените утверждения как в `server_test.go`, так и в `CLI_test.go`.

Тест теперь должен выглядеть так:

```go
//CLI_test.go
func TestCLI(t *testing.T) {
	in := strings.NewReader("Chris wins\n")
	playerStore := &StubPlayerStore{}

	cli := &CLI{playerStore, in}
	cli.PlayPoker()

	assertPlayerWin(t, playerStore, "Chris")
}
```

Теперь давайте напишем _еще один_ тест с другим вводом пользователя, чтобы заставить нас действительно его прочитать.

## Сначала напишите тест

```go
//CLI_test.go
func TestCLI(t *testing.T) {

	t.Run("record chris win from user input", func(t *testing.T) {
		in := strings.NewReader("Chris wins\n")
		playerStore := &StubPlayerStore{}

		cli := &CLI{playerStore, in}
		cli.PlayPoker()

		assertPlayerWin(t, playerStore, "Chris")
	})

	t.Run("record cleo win from user input", func(t *testing.T) {
		in := strings.NewReader("Cleo wins\n")
		playerStore := &StubPlayerStore{}

		cli := &CLI{playerStore, in}
		cli.PlayPoker()

		assertPlayerWin(t, playerStore, "Cleo")
	})

}
```

## Попробуйте запустить тест

```
=== RUN   TestCLI
--- FAIL: TestCLI (0.00s)
=== RUN   TestCLI/record_chris_win_from_user_input
    --- PASS: TestCLI/record_chris_win_from_user_input (0.00s)
=== RUN   TestCLI/record_cleo_win_from_user_input
    --- FAIL: TestCLI/record_cleo_win_from_user_input (0.00s)
        CLI_test.go:27: did not store correct winner got 'Chris' want 'Cleo'
FAIL
```

## Напишите достаточно кода, чтобы он прошел

Мы будем использовать [`bufio.Scanner`](https://golang.org/pkg/bufio/) для чтения ввода из `io.Reader`.

> Пакет `bufio` реализует буферизованный ввод/вывод. Он оборачивает объект `io.Reader` или `io.Writer`, создавая другой объект (Reader или Writer), который также реализует интерфейс, но предоставляет буферизацию и некоторую помощь для текстового ввода/вывода.

Обновите код следующим образом:

```go
//CLI.go
type CLI struct {
	playerStore PlayerStore
	in          io.Reader
}

func (cli *CLI) PlayPoker() {
	reader := bufio.NewScanner(cli.in)
	reader.Scan()
	cli.playerStore.RecordWin(extractWinner(reader.Text()))
}

func extractWinner(userInput string) string {
	return strings.Replace(userInput, " wins", "", 1)
}
```

Теперь тесты пройдут.

-   `Scanner.Scan()` будет читать до символа новой строки.
-   Затем мы используем `Scanner.Text()`, чтобы вернуть `string`, которую прочитал сканер.

Теперь, когда у нас есть проходящие тесты, мы должны подключить это к `main`. Помните, что мы всегда должны стремиться иметь полностью интегрированное работающее программное обеспечение как можно быстрее.

В `main.go` добавьте следующее и запустите. (Возможно, вам придется настроить путь второй зависимости в соответствии с тем, что находится на вашем компьютере)

```go
package main

import (
	"fmt"
	"github.com/quii/learn-go-with-tests/command-line/v3"
	"log"
	"os"
)

const dbFileName = "game.db.json"

func main() {
	fmt.Println("Let's play poker")
	fmt.Println("Type {Name} wins to record a win")

	db, err := os.OpenFile(dbFileName, os.O_RDWR|os.O_CREATE, 0666)

	if err != nil {
		log.Fatalf("problem opening %s %v", dbFileName, err)
	}

	store, err := poker.NewFileSystemPlayerStore(db)

	if err != nil {
		log.Fatalf("problem creating file system player store, %v ", err)
	}

	game := poker.CLI{store, os.Stdin}
	game.PlayPoker()
}
```

Вы должны получить ошибку:

```
command-line/v3/cmd/cli/main.go:32:25: implicit assignment of unexported field 'playerStore' in poker.CLI literal
command-line/v3/cmd/cli/main.go:32:34: implicit assignment of unexported field 'in' in poker.CLI literal
```

Здесь происходит то, что мы пытаемся присвоить значения полям `playerStore` и `in` в `CLI`. Это неэкспортируемые (приватные) поля. Мы _могли бы_ сделать это в нашем тестовом коде, потому что наш тест находится в том же пакете, что и `CLI` (`poker`). Но наш `main` находится в пакете `main`, поэтому у него нет доступа.

Это подчеркивает важность _интеграции вашей работы_. Мы справедливо сделали зависимости нашего `CLI` приватными (потому что мы не хотим, чтобы они были доступны пользователям `CLI`), но не создали способ для пользователей его конструировать.

Есть ли способ выявить эту проблему раньше?

### `package mypackage_test`

Во всех других примерах до сих пор, когда мы создавали тестовый файл, мы объявляли его принадлежащим тому же пакету, который мы тестируем.

Это нормально, и это означает, что в редких случаях, когда мы хотим протестировать что-то внутреннее для пакета, у нас есть доступ к неэкспортируемым типам.

Но, учитывая, что мы выступали за то, чтобы _не_ тестировать внутренние вещи _в общем_, может ли Go помочь в этом? Что если бы мы могли тестировать наш код там, где у нас есть доступ только к экспортируемым типам (как у нашего `main`)?

Когда вы пишете проект с несколькими пакетами, я настоятельно рекомендую, чтобы имя вашего тестового пакета заканчивалось на `_test`. Когда вы это сделаете, вы сможете иметь доступ только к публичным типам в вашем пакете. Это помогло бы в этом конкретном случае, а также помогает привить дисциплину тестирования только публичных API. Если вы все еще хотите тестировать внутренние элементы, вы можете создать отдельный тест с пакетом, который вы хотите протестировать.

Поговорка TDD гласит, что если вы не можете протестировать свой код, то, вероятно, пользователям вашего кода трудно интегрироваться с ним. Использование `package foo_test` поможет в этом, заставляя вас тестировать ваш код так, как если бы вы импортировали его, как это будут делать пользователи вашего пакета.

Прежде чем исправлять `main`, давайте изменим пакет нашего теста внутри `CLI_test.go` на `poker_test`.

Если у вас хорошо настроенная IDE, вы внезапно увидите много красного! Если вы запустите компилятор, вы получите следующие ошибки:

```
./CLI_test.go:12:19: undefined: StubPlayerStore
./CLI_test.go:17:3: undefined: assertPlayerWin
./CLI_test.go:22:19: undefined: StubPlayerStore
./CLI_test.go:27:3: undefined: assertPlayerWin
```

Теперь мы столкнулись с дополнительными вопросами по проектированию пакетов. Чтобы протестировать наше программное обеспечение, мы создали неэкспортируемые заглушки и вспомогательные функции, которые больше недоступны для использования в нашем `CLI_test`, потому что вспомогательные функции определены в файлах `_test.go` в пакете `poker`.

#### Хотим ли мы, чтобы наши заглушки и вспомогательные функции были "публичными"?

Это субъективное обсуждение. Можно утверждать, что вы не хотите загрязнять API вашего пакета кодом для облегчения тестов.

В презентации ["Advanced Testing with Go"](https://speakerdeck.com/mitchellh/advanced-testing-with-go?slide=53) Митчелл Хашимото описывает, как в HashiCorp они выступают за это, чтобы пользователи пакета могли писать тесты, не изобретая заново заглушки. В нашем случае это означало бы, что любой, кто использует наш пакет `poker`, не будет вынужден создавать свой собственный заглушечный `PlayerStore`, если он хочет работать с нашим кодом.

По моему опыту, я использовал эту технику в других общих пакетах, и она оказалась чрезвычайно полезной с точки зрения экономии времени пользователей при интеграции с нашими пакетами.

Итак, давайте создадим файл `testing.go` и добавим туда нашу заглушку и наши вспомогательные функции.

```go
// testing.go
package poker

import "testing"

type StubPlayerStore struct {
	scores   map[string]int
	winCalls []string
	league   []Player
}

func (s *StubPlayerStore) GetPlayerScore(name string) int {
	score := s.scores[name]
	return score
}

func (s *StubPlayerStore) RecordWin(name string) {
	s.winCalls = append(s.winCalls, name)
}

func (s *StubPlayerStore) GetLeague() League {
	return s.league
}

func AssertPlayerWin(t testing.TB, store *StubPlayerStore, winner string) {
	t.Helper()

	if len(store.winCalls) != 1 {
		t.Fatalf("got %d calls to RecordWin want %d", len(store.winCalls), 1)
	}

	if store.winCalls[0] != winner {
		t.Errorf("did not store correct winner got %q want %q", store.winCalls[0], winner)
	}
}

// todo for you - the rest of the helpers
```

Вам нужно будет сделать вспомогательные функции публичными (помните, что экспорт осуществляется с заглавной буквы в начале), если вы хотите, чтобы они были доступны для импортеров нашего пакета.

В нашем тесте `CLI` вам нужно будет вызвать код так, как если бы вы использовали его в другом пакете.

```go
//CLI_test.go
func TestCLI(t *testing.T) {

	t.Run("record chris win from user input", func(t *testing.T) {
		in := strings.NewReader("Chris wins\n")
		playerStore := &poker.StubPlayerStore{}

		cli := &poker.CLI{playerStore, in}
		cli.PlayPoker()

		poker.AssertPlayerWin(t, playerStore, "Chris")
	})

	t.Run("record cleo win from user input", func(t *testing.T) {
		in := strings.NewReader("Cleo wins\n")
		playerStore := &poker.StubPlayerStore{}

		cli := &poker.CLI{playerStore, in}
		cli.PlayPoker()

		poker.AssertPlayerWin(t, playerStore, "Cleo")
	})

}
```

Теперь вы увидите, что у нас те же проблемы, что и в `main`:

```
./CLI_test.go:15:26: implicit assignment of unexported field 'playerStore' in poker.CLI literal
./CLI_test.go:15:39: implicit assignment of unexported field 'in' in poker.CLI literal
./CLI_test.go:25:26: implicit assignment of unexported field 'playerStore' in poker.CLI literal
./CLI_test.go:25:39: implicit assignment of unexported field 'in' in poker.CLI literal
```

Самый простой способ обойти это — создать конструктор, как мы делали для других типов. Мы также изменим `CLI`, чтобы он хранил `bufio.Scanner` вместо `io.Reader`, так как он теперь автоматически оборачивается во время создания.

```go
//CLI.go
type CLI struct {
	playerStore PlayerStore
	in          *bufio.Scanner
}

func NewCLI(store PlayerStore, in io.Reader) *CLI {
	return &CLI{
		playerStore: store,
		in:          bufio.NewScanner(in),
	}
}
```

Сделав это, мы можем упростить и провести рефакторинг нашего кода чтения:

```go
//CLI.go
func (cli *CLI) PlayPoker() {
	userInput := cli.readLine()
	cli.playerStore.RecordWin(extractWinner(userInput))
}

func extractWinner(userInput string) string {
	return strings.Replace(userInput, " wins", "", 1)
}

func (cli *CLI) readLine() string {
	cli.in.Scan()
	return cli.in.Text()
}
```

Измените тест, чтобы он использовал конструктор, и тесты должны снова проходить.

Наконец, мы можем вернуться к нашему новому `main.go` и использовать только что созданный нами конструктор:

```go
//cmd/cli/main.go
game := poker.NewCLI(store, os.Stdin)
```

Попробуйте запустить его, введите "Bob wins".

### Рефакторинг

У нас есть некоторое дублирование в наших соответствующих приложениях, где мы открываем файл и создаем `file_system_store` из его содержимого. Это кажется небольшой слабостью в дизайне нашего пакета, поэтому мы должны создать в нем функцию для инкапсуляции открытия файла из пути и возврата `PlayerStore`.

```go
//file_system_store.go
func FileSystemPlayerStoreFromFile(path string) (*FileSystemPlayerStore, func(), error) {
	db, err := os.OpenFile(path, os.O_RDWR|os.O_CREATE, 0666)

	if err != nil {
		return nil, nil, fmt.Errorf("problem opening %s %v", path, err)
	}

	closeFunc := func() {
		db.Close()
	}

	store, err := NewFileSystemPlayerStore(db)

	if err != nil {
		return nil, nil, fmt.Errorf("problem creating file system player store, %v ", err)
	}

	return store, closeFunc, nil
}
```

Теперь проведите рефакторинг обоих наших приложений, чтобы использовать эту функцию для создания хранилища.

#### Код приложения CLI

```go
// cmd/cli/main.go
package main

import (
	"fmt"
	"github.com/quii/learn-go-with-tests/command-line/v3"
	"log"
	"os"
)

const dbFileName = "game.db.json"

func main() {
	store, close, err := poker.FileSystemPlayerStoreFromFile(dbFileName)

	if err != nil {
		log.Fatal(err)
	}
	defer close()

	fmt.Println("Let's play poker")
	fmt.Println("Type {Name} wins to record a win")
	poker.NewCLI(store, os.Stdin).PlayPoker()
}
```

#### Код приложения веб-сервера

```go
// cmd/webserver/main.go
package main

import (
	"github.com/quii/learn-go-with-tests/command-line/v3"
	"log"
	"net/http"
)

const dbFileName = "game.db.json"

func main() {
	store, close, err := poker.FileSystemPlayerStoreFromFile(dbFileName)

	if err != nil {
		log.Fatal(err)
	}
	defer close()

	server := poker.NewPlayerServer(store)

	if err := http.ListenAndServe(":5000", server); err != nil {
		log.Fatalf("could not listen on port 5000 %v", err)
	}
}
```

Обратите внимание на симметрию: несмотря на разные пользовательские интерфейсы, настройка почти идентична. Это хорошее подтверждение нашего дизайна до сих пор.
И обратите также внимание, что `FileSystemPlayerStoreFromFile` возвращает функцию закрытия, чтобы мы могли закрыть базовый файл после того, как закончим использовать хранилище (Store).

## Завершение

### Структура пакета

Эта глава означала, что мы хотели создать два приложения, повторно используя написанный нами доменный код. Для этого нам потребовалось обновить структуру нашего пакета, чтобы у нас были отдельные папки для наших соответствующих `main` функций.

Сделав это, мы столкнулись с проблемами интеграции из-за неэкспортируемых значений, что еще раз демонстрирует ценность работы небольшими "срезами" и частой интеграции.

Мы узнали, как `mypackage_test` помогает нам создать тестовую среду, которая предоставляет тот же опыт для других пакетов, интегрирующихся с вашим кодом, чтобы помочь вам выявить проблемы интеграции и увидеть, насколько легко (или нет!) работать с вашим кодом.

### Чтение пользовательского ввода

Мы увидели, как легко работать с чтением из `os.Stdin`, поскольку он реализует `io.Reader`. Мы использовали `bufio.Scanner` для легкого построчного чтения пользовательского ввода.

### Простые абстракции ведут к более простому повторному использованию кода

Интеграция `PlayerStore` в наше новое приложение (после корректировки пакетов) не потребовала почти никаких усилий, и последующее тестирование также было очень легким, потому что мы решили предоставить и нашу заглушенную версию.