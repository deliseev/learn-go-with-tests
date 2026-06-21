# Время

[**Весь код для этой главы вы можете найти здесь**](https://github.com/quii/learn-go-with-tests/tree/main/time)

Владелец продукта хочет, чтобы мы расширили функциональность нашего консольного приложения, помогая группе людей играть в техасский холдем.

## Достаточно информации о покере

Вам не нужно много знать о покере, лишь то, что через определённые промежутки времени все игроки должны быть информированы о постоянно растущем значении "блайнда".

Наше приложение поможет отслеживать, когда блайнд должен увеличиваться, и каково должно быть его значение.

* При запуске приложение спрашивает, сколько игроков играет. Это определяет время до увеличения ставки "блайнда".
  * Базовое время составляет 5 минут.
  * За каждого игрока добавляется 1 минута.
  * Например, 6 игроков = 11 минут до увеличения блайнда.
* После истечения времени блайнда игра должна уведомить игроков о новом размере ставки блайнда.
* Блайнд начинается со 100 фишек, затем 200, 400, 600, 1000, 2000 и продолжает удваиваться, пока игра не закончится (наша предыдущая функциональность "Ruth wins" всё ещё должна завершать игру).

## Напоминание о коде

В предыдущей главе мы начали разработку нашего консольного приложения, которое уже принимает команду вида `{name} wins`. Вот как выглядит текущий код `CLI`, но перед началом работы обязательно ознакомьтесь и с другим кодом.

```go
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

### `time.AfterFunc`

Мы хотим иметь возможность запланировать печать значений ставок блайнда в нашей программе через определённые промежутки времени, зависящие от количества игроков.

Чтобы ограничить объем работ, мы пока забудем о количестве игроков и просто предположим, что их 5, так что мы протестируем, что _каждые 10 минут выводится новое значение ставки блайнда_.

Как обычно, стандартная библиотека предлагает нам [`func AfterFunc(d Duration, f func()) *Timer`](https://golang.org/pkg/time/#AfterFunc)

> `AfterFunc` ждёт истечения длительности, а затем вызывает `f` в своей собственной горутине. Он возвращает `Timer`, который можно использовать для отмены вызова с помощью его метода `Stop`.

### [`time.Duration`](https://golang.org/pkg/time/#Duration)

> `Duration` представляет собой прошедшее время между двумя моментами как количество наносекунд в формате `int64`.

Библиотека `time` содержит ряд констант, которые позволяют умножать эти наносекунды, делая их более читаемыми для сценариев, которые мы будем реализовывать.

```
5 * time.Second
```

Когда мы вызываем `PlayPoker`, мы запланируем все наши оповещения о блайнде.

Однако тестирование этого может быть немного сложным. Мы хотим убедиться, что каждый период времени запланирован с правильным значением блайнда, но если вы посмотрите на сигнатуру `time.AfterFunc`, её второй аргумент — это функция, которую она будет выполнять. В Go нельзя сравнивать функции, поэтому мы не сможем проверить, какая функция была передана. Таким образом, нам потребуется написать некую обёртку вокруг `time.AfterFunc`, которая будет принимать время выполнения и сумму для печати, чтобы мы могли "шпионить" за этим.

## Сначала напишите тест

Добавьте новый тест в наш набор тестов.

```go
t.Run("it schedules printing of blind values", func(t *testing.T) {
	in := strings.NewReader("Chris wins\n")
	playerStore := &poker.StubPlayerStore{}
	blindAlerter := &SpyBlindAlerter{}

	cli := poker.NewCLI(playerStore, in, blindAlerter)
	cli.PlayPoker()

	if len(blindAlerter.alerts) != 1 {
		t.Fatal("expected a blind alert to be scheduled")
	}
})
```

Вы заметите, что мы создали `SpyBlindAlerter`, который мы пытаемся внедрить в наш `CLI`, а затем проверяем, что после вызова `PlayPoker` оповещение запланировано.

(Помните, что мы сначала реализуем самый простой сценарий, а затем будем итерироваться.)

Вот определение `SpyBlindAlerter`:

```go
type SpyBlindAlerter struct {
	alerts []struct {
		scheduledAt time.Duration
		amount      int
	}
}

func (s *SpyBlindAlerter) ScheduleAlertAt(duration time.Duration, amount int) {
	s.alerts = append(s.alerts, struct {
		scheduledAt time.Duration
		amount      int
	}{duration, amount})
}
```

## Попробуйте запустить тест

```
./CLI_test.go:32:27: too many arguments in call to poker.NewCLI
	have (*poker.StubPlayerStore, *strings.Reader, *SpyBlindAlerter)
	want (poker.PlayerStore, io.Reader)
```

## Напишите минимальный объём кода, чтобы тест запустился, и проверьте вывод ошибочного теста

Мы добавили новый аргумент, и компилятор жалуется. _Строго говоря_, минимальный объём кода — это заставить `NewCLI` принимать `*SpyBlindAlerter`, но давайте немного схитрим и просто определим зависимость как интерфейс.

```go
type BlindAlerter interface {
	ScheduleAlertAt(duration time.Duration, amount int)
}
```

А затем добавьте его в конструктор.

```go
func NewCLI(store PlayerStore, in io.Reader, alerter BlindAlerter) *CLI
```

Теперь другие ваши тесты не пройдут, так как в `NewCLI` не передан `BlindAlerter`.

"Шпионаж" за `BlindAlerter` не имеет отношения к другим тестам, поэтому в тестовом файле добавьте

```go
var dummySpyAlerter = &SpyBlindAlerter{}
```

Затем используйте его в других тестах, чтобы исправить проблемы компиляции. Пометив его как "заглушку" (dummy), читателю теста становится ясно, что это не важно.

[> Объекты-заглушки (Dummy objects) передаются, но никогда не используются. Обычно они просто служат для заполнения списков параметров.](https://martinfowler.com/articles/mocksArentStubs.html)

Теперь тесты должны компилироваться, и наш новый тест не проходит.

```
=== RUN   TestCLI
=== RUN   TestCLI/it_schedules_printing_of_blind_values
--- FAIL: TestCLI (0.00s)
    --- FAIL: TestCLI/it_schedules_printing_of_blind_values (0.00s)
    	CLI_test.go:38: expected a blind alert to be scheduled
```

## Напишите достаточно кода, чтобы тест прошёл

Нам нужно будет добавить `BlindAlerter` в качестве поля в наш `CLI`, чтобы мы могли ссылаться на него в нашем методе `PlayPoker`.

```go
type CLI struct {
	playerStore PlayerStore
	in          *bufio.Scanner
	alerter     BlindAlerter
}

func NewCLI(store PlayerStore, in io.Reader, alerter BlindAlerter) *CLI {
	return &CLI{
		playerStore: store,
		in:          bufio.NewScanner(in),
		alerter:     alerter,
	}
}
```

Чтобы тест прошёл, мы можем вызвать наш `BlindAlerter` с любыми значениями, которые нам нравятся.

```go
func (cli *CLI) PlayPoker() {
	cli.alerter.ScheduleAlertAt(5*time.Second, 100)
	userInput := cli.readLine()
	cli.playerStore.RecordWin(extractWinner(userInput))
}
```

Далее мы захотим проверить, что он планирует все оповещения, на которые мы рассчитываем, для 5 игроков.

## Сначала напишите тест

```go
	t.Run("it schedules printing of blind values", func(t *testing.T) {
		in := strings.NewReader("Chris wins\n")
		playerStore := &poker.StubPlayerStore{}
		blindAlerter := &SpyBlindAlerter{}

		cli := poker.NewCLI(playerStore, in, blindAlerter)
		cli.PlayPoker()

		cases := []struct {
			expectedScheduleTime time.Duration
			expectedAmount       int
		}{
			{0 * time.Second, 100},
			{10 * time.Minute, 200},
			{20 * time.Minute, 300},
			{30 * time.Minute, 400},
			{40 * time.Minute, 500},
			{50 * time.Minute, 600},
			{60 * time.Minute, 800},
			{70 * time.Minute, 1000},
			{80 * time.Minute, 2000},
			{90 * time.Minute, 4000},
			{100 * time.Minute, 8000},
		}

		for i, c := range cases {
			t.Run(fmt.Sprintf("%d scheduled for %v", c.expectedAmount, c.expectedScheduleTime), func(t *testing.T) {

				if len(blindAlerter.alerts) <= i {
					t.Fatalf("alert %d was not scheduled %v", i, blindAlerter.alerts)
				}

				alert := blindAlerter.alerts[i]

				amountGot := alert.amount
				if amountGot != c.expectedAmount {
					t.Errorf("got amount %d, want %d", amountGot, c.expectedAmount)
				}

				gotScheduledTime := alert.scheduledAt
				if gotScheduledTime != c.expectedScheduleTime {
					t.Errorf("got scheduled time of %v, want %v", gotScheduledTime, c.expectedScheduleTime)
				}
			})
		}
	})
```

Табличный тест здесь хорошо работает и наглядно иллюстрирует наши требования. Мы проходим по таблице и проверяем `SpyBlindAlerter`, чтобы убедиться, что оповещение было запланировано с правильными значениями.

## Попробуйте запустить тест

Вы должны увидеть много ошибок, выглядящих примерно так:

```
=== RUN   TestCLI
--- FAIL: TestCLI (0.00s)
=== RUN   TestCLI/it_schedules_printing_of_blind_values
    --- FAIL: TestCLI/it_schedules_printing_of_blind_values (0.00s)
=== RUN   TestCLI/it_schedules_printing_of_blind_values/100_scheduled_for_0s
        --- FAIL: TestCLI/it_schedules_printing_of_blind_values/100_scheduled_for_0s (0.00s)
        	CLI_test.go:71: got scheduled time of 5s, want 0s
=== RUN   TestCLI/it_schedules_printing_of_blind_values/200_scheduled_for_10m0s
        --- FAIL: TestCLI/it_schedules_printing_of_blind_values/200_scheduled_for_10m0s (0.00s)
        	CLI_test.go:59: alert 1 was not scheduled [{5000000000 100}]
```

## Напишите достаточно кода, чтобы тест прошёл

```go
func (cli *CLI) PlayPoker() {

	blinds := []int{100, 200, 300, 400, 500, 600, 800, 1000, 2000, 4000, 8000}
	blindTime := 0 * time.Second
	for _, blind := range blinds {
		cli.alerter.ScheduleAlertAt(blindTime, blind)
		blindTime = blindTime + 10*time.Minute
	}

	userInput := cli.readLine()
	cli.playerStore.RecordWin(extractWinner(userInput))
}
```

Это не намного сложнее того, что у нас уже было. Теперь мы просто итерируемся по массиву `blinds` и вызываем планировщик с увеличивающимся `blindTime`.

## Рефакторинг

Мы можем инкапсулировать наши запланированные оповещения в метод, чтобы `PlayPoker` читался немного яснее.

```go
func (cli *CLI) PlayPoker() {
	cli.scheduleBlindAlerts()
	userInput := cli.readLine()
	cli.playerStore.RecordWin(extractWinner(userInput))
}

func (cli *CLI) scheduleBlindAlerts() {
	blinds := []int{100, 200, 300, 400, 500, 600, 800, 1000, 2000, 4000, 8000}
	blindTime := 0 * time.Second
	for _, blind := range blinds {
		cli.alerter.ScheduleAlertAt(blindTime, blind)
		blindTime = blindTime + 10*time.Minute
	}
}
```

Наконец, наши тесты выглядят немного громоздко. У нас есть две анонимные структуры, представляющие одно и то же: `ScheduledAlert`. Давайте преобразуем это в новый тип, а затем создадим несколько вспомогательных функций для их сравнения.

```go
type scheduledAlert struct {
	at     time.Duration
	amount int
}

func (s scheduledAlert) String() string {
	return fmt.Sprintf("%d chips at %v", s.amount, s.at)
}

type SpyBlindAlerter struct {
	alerts []scheduledAlert
}

func (s *SpyBlindAlerter) ScheduleAlertAt(at time.Duration, amount int) {
	s.alerts = append(s.alerts, scheduledAlert{at, amount})
}
```

Мы добавили метод `String()` к нашему типу, чтобы он красиво выводился, если тест не проходит.

Обновите наш тест, чтобы использовать наш новый тип.

```go
t.Run("it schedules printing of blind values", func(t *testing.T) {
	in := strings.NewReader("Chris wins\n")
	playerStore := &poker.StubPlayerStore{}
	blindAlerter := &SpyBlindAlerter{}

	cli := poker.NewCLI(playerStore, in, blindAlerter)
	cli.PlayPoker()

	cases := []scheduledAlert{
		{0 * time.Second, 100},
		{10 * time.Minute, 200},
		{20 * time.Minute, 300},
		{30 * time.Minute, 400},
		{40 * time.Minute, 500},
		{50 * time.Minute, 600},
		{60 * time.Minute, 800},
		{70 * time.Minute, 1000},
		{80 * time.Minute, 2000},
		{90 * time.Minute, 4000},
		{100 * time.Minute, 8000},
	}

	for i, want := range cases {
		t.Run(fmt.Sprint(want), func(t *testing.T) {

			if len(blindAlerter.alerts) <= i {
				t.Fatalf("alert %d was not scheduled %v", i, blindAlerter.alerts)
			}

			got := blindAlerter.alerts[i]
			assertScheduledAlert(t, got, want)
		})
	}
})
```

Реализуйте `assertScheduledAlert` самостоятельно.

Мы потратили здесь достаточно много времени на написание тестов и были немного "непослушными", не интегрируя это с нашим приложением. Давайте исправим это, прежде чем добавлять новые требования.

Попробуйте запустить приложение, и оно не скомпилируется, жалуясь на недостаточное количество аргументов для `NewCLI`.

Давайте создадим реализацию `BlindAlerter`, которую мы сможем использовать в нашем приложении.

Создайте `blind_alerter.go` и переместите наш интерфейс `BlindAlerter`, а также добавьте новые элементы ниже.

```go
package poker

import (
	"fmt"
	"os"
	"time"
)

type BlindAlerter interface {
	ScheduleAlertAt(duration time.Duration, amount int)
}

type BlindAlerterFunc func(duration time.Duration, amount int)

func (a BlindAlerterFunc) ScheduleAlertAt(duration time.Duration, amount int) {
	a(duration, amount)
}

func StdOutAlerter(duration time.Duration, amount int) {
	time.AfterFunc(duration, func() {
		fmt.Fprintf(os.Stdout, "Blind is now %d\n", amount)
	})
}
```

Помните, что любой _тип_ может реализовывать интерфейс, а не только `структуры`. Если вы создаёте библиотеку, которая предоставляет интерфейс с одной определённой функцией, то часто используется идиома, при которой также предоставляется тип `MyInterfaceFunc`.

Этот тип будет функцией, которая также будет реализовывать ваш интерфейс. Таким образом, пользователи вашего интерфейса могут реализовать его с помощью всего лишь функции; вместо того, чтобы создавать пустой тип `структуры`.

Затем мы создаём функцию `StdOutAlerter`, которая имеет ту же сигнатуру, что и функция, и просто используем `time.AfterFunc` для планирования её печати в `os.Stdout`.

Обновите `main` там, где мы создаём `NewCLI`, чтобы увидеть это в действии.

```go
poker.NewCLI(store, os.Stdin, poker.BlindAlerterFunc(poker.StdOutAlerter)).PlayPoker()
```

Перед запуском вы можете захотеть изменить приращение `blindTime` в `CLI` на 10 секунд вместо 10 минут, просто чтобы увидеть это в действии.

Вы должны увидеть, как он выводит значения блайнда каждые 10 секунд, как мы и ожидали. Обратите внимание, что вы всё ещё можете ввести `Shaun wins` в CLI, и программа завершится, как мы и ожидали.

Игра не всегда будет играться с 5 людьми, поэтому нам нужно запросить у пользователя количество игроков перед началом игры.

## Сначала напишите тест

Чтобы проверить, запрашиваем ли мы количество игроков, мы захотим записать то, что выводится в `StdOut`. Мы делали это несколько раз, и мы знаем, что `os.Stdout` — это `io.Writer`, поэтому мы можем проверить, что записывается, если мы используем внедрение зависимостей для передачи `bytes.Buffer` в наш тест и видим, что наш код будет записывать.

Мы пока не заботимся о других наших "сотрудниках" в этом тесте, поэтому мы создали несколько заглушек в нашем тестовом файле.

Нам следует быть немного осторожными, так как теперь у нас 4 зависимости для `CLI`, это похоже на то, что он начинает брать на себя слишком много обязанностей. Давайте пока с этим смиримся и посмотрим, не появится ли рефакторинг по мере добавления этой новой функциональности.

```go
var dummyBlindAlerter = &SpyBlindAlerter{}
var dummyPlayerStore = &poker.StubPlayerStore{}
var dummyStdIn = &bytes.Buffer{}
var dummyStdOut = &bytes.Buffer{}
```

Вот наш новый тест:

```go
t.Run("it prompts the user to enter the number of players", func(t *testing.T) {
	stdout := &bytes.Buffer{}
	cli := poker.NewCLI(dummyPlayerStore, dummyStdIn, stdout, dummyBlindAlerter)
	cli.PlayPoker()

	got := stdout.String()
	want := "Please enter the number of players: "

	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
})
```

Мы передаём то, что будет `os.Stdout` в `main`, и смотрим, что записывается.

## Попробуйте запустить тест

```
./CLI_test.go:38:27: too many arguments in call to poker.NewCLI
	have (*poker.StubPlayerStore, *bytes.Buffer, *bytes.Buffer, *SpyBlindAlerter)
	want (poker.PlayerStore, io.Reader, poker.BlindAlerter)
```

## Напишите минимальный объём кода, чтобы тест запустился, и проверьте вывод ошибочного теста

У нас новая зависимость, поэтому нам придётся обновить `NewCLI`.

```go
func NewCLI(store PlayerStore, in io.Reader, out io.Writer, alerter BlindAlerter) *CLI
```

Теперь _другие_ тесты не скомпилируются, потому что в `NewCLI` не передан `io.Writer`.

Добавьте `dummyStdOut` для других тестов.

Новый тест должен завершиться неудачей следующим образом:

```
=== RUN   TestCLI
--- FAIL: TestCLI (0.00s)
=== RUN   TestCLI/it_prompts_the_user_to_enter_the_number_of_players
    --- FAIL: TestCLI/it_prompts_the_user_to_enter_the_number_of_players (0.00s)
    	CLI_test.go:46: got '', want 'Please enter the number of players: '
FAIL
```

## Напишите достаточно кода, чтобы тест прошёл

Нам нужно добавить нашу новую зависимость в наш `CLI`, чтобы мы могли ссылаться на неё в `PlayPoker`.

```go
type CLI struct {
	playerStore PlayerStore
	in          *bufio.Scanner
	out         io.Writer
	alerter     BlindAlerter
}

func NewCLI(store PlayerStore, in io.Reader, out io.Writer, alerter BlindAlerter) *CLI {
	return &CLI{
		playerStore: store,
		in:          bufio.NewScanner(in),
		out:         out,
		alerter:     alerter,
	}
}
```

Затем, наконец, мы можем написать наше приглашение в начале игры.

```go
func (cli *CLI) PlayPoker() {
	fmt.Fprint(cli.out, "Please enter the number of players: ")
	cli.scheduleBlindAlerts()
	userInput := cli.readLine()
	cli.playerStore.RecordWin(extractWinner(userInput))
}
```

## Рефакторинг

У нас есть дублирующаяся строка для приглашения, которую мы должны вынести в константу.

```go
const PlayerPrompt = "Please enter the number of players: "
```

Используйте это как в тестовом коде, так и в `CLI`.

Теперь нам нужно ввести число и извлечь его. Единственный способ узнать, был ли достигнут желаемый эффект, — это посмотреть, какие оповещения о блайнде были запланированы.

## Сначала напишите тест

```go
t.Run("it prompts the user to enter the number of players", func(t *testing.T) {
	stdout := &bytes.Buffer{}
	in := strings.NewReader("7\n")
	blindAlerter := &SpyBlindAlerter{}

	cli := poker.NewCLI(dummyPlayerStore, in, stdout, blindAlerter)
	cli.PlayPoker()

	got := stdout.String()
	want := poker.PlayerPrompt

	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}

	cases := []scheduledAlert{
		{0 * time.Second, 100},
		{12 * time.Minute, 200},
		{24 * time.Minute, 300},
		{36 * time.Minute, 400},
	}

	for i, want := range cases {
		t.Run(fmt.Sprint(want), func(t *testing.T) {

			if len(blindAlerter.alerts) <= i {
				t.Fatalf("alert %d was not scheduled %v", i, blindAlerter.alerts)
			}

			got := blindAlerter.alerts[i]
			assertScheduledAlert(t, got, want)
		})
	}
})
```

Ой! Много изменений.

* Мы удаляем нашу заглушку для `StdIn` и вместо этого отправляем "замоканную" версию, представляющую ввод пользователем числа 7.
* Мы также удаляем нашу заглушку для `blind alerter`, чтобы мы могли видеть, что количество игроков повлияло на планирование.
* Мы тестируем, какие оповещения запланированы.

## Попробуйте запустить тест

Тест должен по-прежнему компилироваться и завершаться ошибкой, сообщающей, что запланированное время неверно, потому что мы жёстко закодировали игру для 5 игроков.

```
=== RUN   TestCLI
--- FAIL: TestCLI (0.00s)
=== RUN   TestCLI/it_prompts_the_user_to_enter_the_number_of_players
    --- FAIL: TestCLI/it_prompts_the_user_to_enter_the_number_of_players (0.00s)
=== RUN   TestCLI/it_prompts_the_user_to_enter_the_number_of_players/100_chips_at_0s
        --- PASS: TestCLI/it_prompts_the_user_to_enter_the_number_of_players/100_chips_at_0s (0.00s)
=== RUN   TestCLI/it_prompts_the_user_to_enter_the_number_of_players/200_chips_at_12m0s
```

## Напишите достаточно кода, чтобы тест прошёл

Помните, мы вольны совершать любые "грехи", которые нам нужны, чтобы это заработало. Как только у нас будет рабочее программное обеспечение, мы сможем заняться рефакторингом того беспорядка, который мы собираемся устроить!

```go
func (cli *CLI) PlayPoker() {
	fmt.Fprint(cli.out, PlayerPrompt)

	numberOfPlayers, _ := strconv.Atoi(cli.readLine())

	cli.scheduleBlindAlerts(numberOfPlayers)

	userInput := cli.readLine()
	cli.playerStore.RecordWin(extractWinner(userInput))
}

func (cli *CLI) scheduleBlindAlerts(numberOfPlayers int) {
	blindIncrement := time.Duration(5+numberOfPlayers) * time.Minute

	blinds := []int{100, 200, 300, 400, 500, 600, 800, 1000, 2000, 4000, 8000}
	blindTime := 0 * time.Second
	for _, blind := range blinds {
		cli.alerter.ScheduleAlertAt(blindTime, blind)
		blindTime = blindTime + blindIncrement
	}
}
```

* Мы считываем `numberOfPlayersInput` в строку.
* Мы используем `cli.readLine()` для получения ввода от пользователя, а затем вызываем `Atoi` для преобразования его в целое число, игнорируя любые сценарии ошибок. Нам потребуется написать тест для этого сценария позже.
* Отсюда мы меняем `scheduleBlindAlerts`, чтобы он принимал количество игроков. Затем мы вычисляем время `blindIncrement`, которое будем использовать для добавления к `blindTime` по мере итерации по значениям блайндов.

Хотя наш новый тест был исправлен, многие другие не прошли, потому что теперь наша система работает только в том случае, если игра начинается с ввода пользователем числа. Вам нужно будет исправить тесты, изменив пользовательский ввод так, чтобы число, за которым следует перевод строки, было добавлено (это подчёркивает ещё больше недостатков в нашем текущем подходе).

## Рефакторинг

Всё это кажется немного ужасным, верно? Давайте **прислушаемся к нашим тестам**.

* Чтобы проверить, что мы планируем какие-либо оповещения, мы настроили 4 различные зависимости. Всякий раз, когда у вас много зависимостей для какой-либо _сущности_ в вашей системе, это подразумевает, что она делает слишком много. Визуально мы видим это по тому, насколько загромождён наш тест.
* Мне кажется, что **нам нужно создать более чистую абстракцию между чтением пользовательского ввода и бизнес-логикой, которую мы хотим реализовать**.
* Лучшим тестом было бы _при заданном пользовательском вводе вызываем ли мы новый тип `Game` с правильным количеством игроков_.
* Затем мы вынесем тестирование планирования в тесты для нашей новой `Game`.

Мы можем сначала выполнить рефакторинг в сторону нашей `Game`, и наш тест должен продолжать проходить. Как только мы внесём желаемые структурные изменения, мы сможем подумать о том, как провести рефакторинг тестов, чтобы отразить наше новое разделение ответственности.

Помните, что при внесении изменений в рефакторинг старайтесь делать их как можно меньше и продолжайте перезапускать тесты.

Попробуйте сначала сами. Подумайте о границах того, что должна предлагать `Game`, и что должен делать наш `CLI`.

Пока **не** меняйте внешний интерфейс `NewCLI`, так как мы не хотим одновременно изменять тестовый код и клиентский код — это слишком много, чтобы жонглировать, и мы можем в итоге что-то сломать.

Вот что у меня получилось:

```go
// game.go
type Game struct {
	alerter BlindAlerter
	store   PlayerStore
}

func (p *Game) Start(numberOfPlayers int) {
	blindIncrement := time.Duration(5+numberOfPlayers) * time.Minute

	blinds := []int{100, 200, 300, 400, 500, 600, 800, 1000, 2000, 4000, 8000}
	blindTime := 0 * time.Second
	for _, blind := range blinds {
		p.alerter.ScheduleAlertAt(blindTime, blind)
		blindTime = blindTime + blindIncrement
	}
}

func (p *Game) Finish(winner string) {
	p.store.RecordWin(winner)
}

// cli.go
type CLI struct {
	in   *bufio.Scanner
	out  io.Writer
	game *Game
}

func NewCLI(store PlayerStore, in io.Reader, out io.Writer, alerter BlindAlerter) *CLI {
	return &CLI{
		in:  bufio.NewScanner(in),
		out: out,
		game: &Game{
			alerter: alerter,
			store:   store,
		},
	}
}

const PlayerPrompt = "Please enter the number of players: "

func (cli *CLI) PlayPoker() {
	fmt.Fprint(cli.out, PlayerPrompt)

	numberOfPlayersInput := cli.readLine()
	numberOfPlayers, _ := strconv.Atoi(strings.Trim(numberOfPlayersInput, "\n"))

	cli.game.Start(numberOfPlayers)

	winnerInput := cli.readLine()
	winner := extractWinner(winnerInput)

	cli.game.Finish(winner)
}

func extractWinner(userInput string) string {
	return strings.Replace(userInput, " wins\n", "", 1)
}

func (cli *CLI) readLine() string {
	cli.in.Scan()
	return cli.in.Text()
}
```

С "доменной" точки зрения:

* Мы хотим `Start` (начать) `Game`, указывая, сколько людей играет.
* Мы хотим `Finish` (завершить) `Game`, объявляя победителя.

Новый тип `Game` инкапсулирует это для нас.

С этим изменением мы передали `BlindAlerter` и `PlayerStore` в `Game`, поскольку теперь он отвечает за оповещения и хранение результатов.

Наш `CLI` теперь заботится только о следующем:

* Создании `Game` с его существующими зависимостями (что мы переделаем далее).
* Интерпретации пользовательского ввода как вызовов методов для `Game`.

Мы хотим стараться избегать "больших" рефакторингов, которые оставляют нас в состоянии неработающих тестов на длительные периоды, так как это увеличивает вероятность ошибок. (Если вы работаете в большой/распределённой команде, это особенно важно).

Первое, что мы сделаем, это переработаем `Game` так, чтобы мы внедряли его в `CLI`. Мы внесём минимальные изменения в наши тесты, чтобы облегчить это, а затем посмотрим, как мы можем разбить тесты на темы, связанные с разбором пользовательского ввода и управлением игрой.

Всё, что нам нужно сделать прямо сейчас, это изменить `NewCLI`.

```go
func NewCLI(in io.Reader, out io.Writer, game *Game) *CLI {
	return &CLI{
		in:   bufio.NewScanner(in),
		out:  out,
		game: game,
	}
}
```

Это уже кажется улучшением. У нас меньше зависимостей, и _наш список зависимостей отражает нашу общую цель проектирования_: `CLI` занимается вводом/выводом и делегирует действия, специфичные для игры, типу `Game`.

Если вы попробуете скомпилировать, возникнут проблемы. Вы должны быть в состоянии исправить эти проблемы самостоятельно. Не беспокойтесь о создании моков для `Game` прямо сейчас, просто инициализируйте _реальные_ `Game`s, чтобы всё скомпилировалось, а тесты стали зелёными.

Для этого вам нужно будет создать конструктор.

```go
func NewGame(alerter BlindAlerter, store PlayerStore) *Game {
	return &Game{
		alerter: alerter,
		store:   store,
	}
}
```

Вот пример одной из исправленных настроек для тестов:

```go
stdout := &bytes.Buffer{}
in := strings.NewReader("7\n")
blindAlerter := &SpyBlindAlerter{}
game := poker.NewGame(blindAlerter, dummyPlayerStore)

cli := poker.NewCLI(in, stdout, game)
cli.PlayPoker()
```

Не должно потребоваться много усилий, чтобы исправить тесты и снова увидеть "зелёные" результаты (в этом и суть!), но убедитесь, что вы также исправили `main.go` перед следующим этапом.

```go
// main.go
game := poker.NewGame(poker.BlindAlerterFunc(poker.StdOutAlerter), store)
cli := poker.NewCLI(os.Stdin, os.Stdout, game)
cli.PlayPoker()
```

Теперь, когда мы вынесли `Game`, мы должны переместить наши специфичные для игры утверждения в тесты, отделённые от `CLI`.

Это просто упражнение по копированию наших тестов `CLI`, но с меньшим количеством зависимостей.

```go
func TestGame_Start(t *testing.T) {
	t.Run("schedules alerts on game start for 5 players", func(t *testing.T) {
		blindAlerter := &poker.SpyBlindAlerter{}
		game := poker.NewGame(blindAlerter, dummyPlayerStore)

		game.Start(5)

		cases := []poker.ScheduledAlert{
			{At: 0 * time.Second, Amount: 100},
			{At: 10 * time.Minute, Amount: 200},
			{At: 20 * time.Minute, Amount: 300},
			{At: 30 * time.Minute, Amount: 400},
			{At: 40 * time.Minute, Amount: 500},
			{At: 50 * time.Minute, Amount: 600},
			{At: 60 * time.Minute, Amount: 800},
			{At: 70 * time.Minute, Amount: 1000},
			{At: 80 * time.Minute, Amount: 2000},
			{At: 90 * time.Minute, Amount: 4000},
			{At: 100 * time.Minute, Amount: 8000},
		}

		checkSchedulingCases(cases, t, blindAlerter)
	})

	t.Run("schedules alerts on game start for 7 players", func(t *testing.T) {
		blindAlerter := &poker.SpyBlindAlerter{}
		game := poker.NewGame(blindAlerter, dummyPlayerStore)

		game.Start(7)

		cases := []poker.ScheduledAlert{
			{At: 0 * time.Second, Amount: 100},
			{At: 12 * time.Minute, Amount: 200},
			{At: 24 * time.Minute, Amount: 300},
			{At: 36 * time.Minute, Amount: 400},
		}

		checkSchedulingCases(cases, t, blindAlerter)
	})

}

func TestGame_Finish(t *testing.T) {
	store := &poker.StubPlayerStore{}
	game := poker.NewGame(dummyBlindAlerter, store)
	winner := "Ruth"

	game.Finish(winner)
	poker.AssertPlayerWin(t, store, winner)
}
```

Теперь гораздо яснее, что происходит, когда начинается игра в покер.

Убедитесь, что вы также перенесли тест для случая завершения игры.

Как только мы убедимся, что перенесли тесты для игровой логики, мы сможем упростить наши тесты `CLI`, чтобы они более чётко отражали наши предполагаемые обязанности.

* Обрабатывать ввод пользователя и вызывать методы `Game` при необходимости.
* Отправлять вывод.
* Важно то, что он не знает о фактической работе игр.

Для этого нам придётся сделать так, чтобы `CLI` больше не зависел от конкретного типа `Game`, а вместо этого принимал интерфейс с `Start(numberOfPlayers)` и `Finish(winner)`. Затем мы сможем создать "шпиона" этого типа и проверять, что делаются правильные вызовы.

Здесь мы понимаем, что иногда именование бывает неловким. Переименуем `Game` в `TexasHoldem` (поскольку это _тип_ игры, в которую мы играем), а новый интерфейс будет называться `Game`. Это соответствует идее, что наш `CLI` не знает, в какую именно игру мы играем и что происходит, когда вы `Start` и `Finish`.

```go
type Game interface {
	Start(numberOfPlayers int)
	Finish(winner string)
}
```

Замените все ссылки на `*Game` внутри `CLI` на `Game` (наш новый интерфейс). Как всегда, продолжайте перезапускать тесты, чтобы убедиться, что всё работает, пока мы проводим рефакторинг.

Теперь, когда мы отделили `CLI` от `TexasHoldem`, мы можем использовать "шпионов" для проверки того, что `Start` и `Finish` вызываются, когда мы этого ожидаем, с правильными аргументами.

Создайте "шпиона", который реализует `Game`.

```go
type GameSpy struct {
	StartedWith  int
	FinishedWith string
}

func (g *GameSpy) Start(numberOfPlayers int) {
	g.StartedWith = numberOfPlayers
}

func (g *GameSpy) Finish(winner string) {
	g.FinishedWith = winner
}
```

Замените любой тест `CLI`, который проверяет логику, специфичную для игры, проверками того, как вызывается наш `GameSpy`. Это затем ясно отразит обязанности `CLI` в наших тестах.

Вот пример одного из исправленных тестов; попробуйте сделать остальное сами и проверьте исходный код, если застрянете.

```go
	t.Run("it prompts the user to enter the number of players and starts the game", func(t *testing.T) {
		stdout := &bytes.Buffer{}
		in := strings.NewReader("7\n")
		game := &GameSpy{}

		cli := poker.NewCLI(in, stdout, game)
		cli.PlayPoker()

		gotPrompt := stdout.String()
		wantPrompt := poker.PlayerPrompt

		if gotPrompt != wantPrompt {
			t.Errorf("got %q, want %q", gotPrompt, wantPrompt)
		}

		if game.StartedWith != 7 {
			t.Errorf("wanted Start called with 7 but got %d", game.StartedWith)
		}
	})
```

Теперь, когда у нас есть чёткое разделение ответственности, проверка граничных случаев, связанных с вводом-выводом, в нашем `CLI` должна быть проще.

Нам нужно рассмотреть сценарий, когда пользователь вводит нечисловое значение при запросе количества игроков:

Наш код не должен начинать игру, а должен выводить удобное сообщение об ошибке пользователю, а затем завершать работу.

## Сначала напишите тест

Начнём с того, что убедимся, что игра не начинается.

```go
t.Run("it prints an error when a non numeric value is entered and does not start the game", func(t *testing.T) {
	stdout := &bytes.Buffer{}
	in := strings.NewReader("Pies\n")
	game := &GameSpy{}

	cli := poker.NewCLI(in, stdout, game)
	cli.PlayPoker()

	if game.StartCalled {
		t.Errorf("game should not have started")
	}
})
```

Вам нужно будет добавить в наш `GameSpy` поле `StartCalled`, которое будет устанавливаться только в том случае, если вызван `Start`.

## Попробуйте запустить тест

```
=== RUN   TestCLI/it_prints_an_error_when_a_non_numeric_value_is_entered_and_does_not_start_the_game
    --- FAIL: TestCLI/it_prints_an_error_when_a_non_numeric_value_is_entered_and_does_not_start_the_game (0.00s)
        CLI_test.go:62: game should not have started
```

## Напишите достаточно кода, чтобы тест прошёл

Там, где мы вызываем `Atoi`, нам просто нужно проверить наличие ошибки.

```go
numberOfPlayers, err := strconv.Atoi(cli.readLine())

if err != nil {
	return
}
```

Далее нам нужно сообщить пользователю, что он сделал неправильно, поэтому мы сделаем утверждение о том, что выводится в `stdout`.

## Сначала напишите тест

Мы уже проверяли, что было выведено в `stdout`, поэтому можем пока скопировать этот код.

```go
gotPrompt := stdout.String()

wantPrompt := poker.PlayerPrompt + "you're so silly"

if gotPrompt != wantPrompt {
	t.Errorf("got %q, want %q", gotPrompt, wantPrompt)
}
```

Мы сохраняем _всё_, что записывается в `stdout`, поэтому мы по-прежнему ожидаем `poker.PlayerPrompt`. Затем мы просто проверяем, что выводится дополнительная вещь. Нас пока не слишком беспокоит точная формулировка, мы займёмся этим при рефакторинге.

## Попробуйте запустить тест

```
=== RUN   TestCLI/it_prints_an_error_when_a_non_numeric_value_is_entered_and_does_not_start_the_game
    --- FAIL: TestCLI/it_prints_an_error_when_a_non_numeric_value_is_entered_and_does_not_start_the_game (0.00s)
        CLI_test.go:70: got 'Please enter the number of players: ', want 'Please enter the number of players: you're so silly'
```

## Напишите достаточно кода, чтобы тест прошёл

Измените код обработки ошибок.

```go
if err != nil {
	fmt.Fprint(cli.out, "you're so silly")
	return
}
```

## Рефакторинг

Теперь вынесите сообщение в константу, как `PlayerPrompt`.

```go
wantPrompt := poker.PlayerPrompt + poker.BadPlayerInputErrMsg
```

и вставьте более подходящее сообщение.

```go
const BadPlayerInputErrMsg = "Bad value received for number of players, please try again with a number"
```

Наконец, наше тестирование того, что было отправлено в `stdout`, довольно многословно, давайте напишем функцию `assert`, чтобы упростить его.

```go
func assertMessagesSentToUser(t testing.TB, stdout *bytes.Buffer, messages ...string) {
	t.Helper()
	want := strings.Join(messages, "")
	got := stdout.String()
	if got != want {
		t.Errorf("got %q sent to stdout but expected %+v", got, messages)
	}
}
```

Использование синтаксиса переменного числа аргументов (`...string`) здесь удобно, потому что нам нужно делать утверждения для разного количества сообщений.

Используйте эту вспомогательную функцию в обоих тестах, где мы делаем утверждения о сообщениях, отправленных пользователю.

Существует ряд тестов, которым могли бы помочь некоторые функции `assertX`, так что попрактикуйтесь в рефакторинге, очистив наши тесты, чтобы они читались лучше.

Потратьте некоторое время и подумайте о ценности некоторых тестов, которые мы разработали. Помните, что нам не нужно больше тестов, чем необходимо, можете ли вы переработать/удалить некоторые из них _и при этом быть уверенными, что всё работает_?

Вот что у меня получилось:

```go
func TestCLI(t *testing.T) {

	t.Run("start game with 3 players and finish game with 'Chris' as winner", func(t *testing.T) {
		game := &GameSpy{}
		stdout := &bytes.Buffer{}

		in := userSends("3", "Chris wins")
		cli := poker.NewCLI(in, stdout, game)

		cli.PlayPoker()

		assertMessagesSentToUser(t, stdout, poker.PlayerPrompt)
		assertGameStartedWith(t, game, 3)
		assertFinishCalledWith(t, game, "Chris")
	})

	t.Run("start game with 8 players and record 'Cleo' as winner", func(t *testing.T) {
		game := &GameSpy{}

		in := userSends("8", "Cleo wins")
		cli := poker.NewCLI(in, dummyStdOut, game)

		cli.PlayPoker()

		assertGameStartedWith(t, game, 8)
		assertFinishCalledWith(t, game, "Cleo")
	})

	t.Run("it prints an error when a non numeric value is entered and does not start the game", func(t *testing.T) {
		game := &GameSpy{}

		stdout := &bytes.Buffer{}
		in := userSends("pies")

		cli := poker.NewCLI(in, stdout, game)
		cli.PlayPoker()

		assertGameNotStarted(t, game)
		assertMessagesSentToUser(t, stdout, poker.PlayerPrompt, poker.BadPlayerInputErrMsg)
	})
}
```

Тесты теперь отражают основные возможности `CLI`: он способен считывать пользовательский ввод о количестве игроков и победителе, а также обрабатывает случаи, когда введено неверное значение для количества игроков. Делая это, читателю становится ясно, что делает `CLI`, а также что он не делает.

Что произойдёт, если вместо `Ruth wins` пользователь введёт `Lloyd is a killer`?

Завершите эту главу, написав тест для этого сценария и заставив его пройти.

## Заключение

### Краткий обзор проекта

За последние 5 глав мы постепенно разработали значительный объём кода, используя TDD.

* У нас есть два приложения: консольное приложение и веб-сервер.
* Оба этих приложения зависят от `PlayerStore` для записи победителей.
* Веб-сервер также может отображать турнирную таблицу, показывающую, кто выигрывает больше всего игр.
* Консольное приложение помогает игрокам в покер, отслеживая текущее значение блайнда.

### `time.Afterfunc`

Очень удобный способ запланировать вызов функции после определённой длительности. Стоит потратить время на [изучение документации по `time`](https://golang.org/pkg/time/), так как она содержит множество функций и методов, экономящих время, с которыми вы можете работать.

Некоторые из моих любимых:

* `time.After(duration)` возвращает `chan Time` после истечения указанной длительности. Так что если вы хотите сделать что-то _после_ определённого времени, это может помочь.
* `time.NewTicker(duration)` возвращает `Ticker`, который похож на вышеупомянутый тем, что возвращает канал, но этот "тикает" каждую длительность, а не только один раз. Это очень удобно, если вы хотите выполнять некоторый код каждую `N длительность`.

### Больше примеров хорошего разделения ответственности

_В целом_, хорошей практикой является отделение ответственности за обработку пользовательского ввода и ответов от доменного кода. Вы видите это здесь в нашем консольном приложении, а также в нашем веб-сервере.

Наши тесты стали запутанными. У нас было слишком много утверждений (проверить этот ввод, запланировать эти оповещения и т.д.) и слишком много зависимостей. Мы визуально видели, что они загромождены; **очень важно прислушиваться к нашим тестам**.

* Если ваши тесты выглядят беспорядочно, попробуйте их рефакторинг.
* Если вы это сделали, и они всё ещё беспорядочны, это, скорее всего, указывает на недостаток в вашем дизайне.
* В этом заключается одна из настоящих сильных сторон тестов.

Хотя тесты и рабочий код были немного загромождены, мы могли свободно проводить рефакторинг, опираясь на наши тесты.

Помните, что, попадая в такие ситуации, всегда делайте маленькие шаги и перезапускайте тесты после каждого изменения.

Было бы опасно одновременно рефакторить _и_ тестовый код, _и_ рабочий код, поэтому мы сначала переработали рабочий код (в текущем состоянии мы не могли сильно улучшить тесты), не меняя его интерфейс, чтобы мы могли максимально полагаться на наши тесты во время изменений. _Затем_ мы переработали тесты после улучшения дизайна.

После рефакторинга список зависимостей отражал нашу цель дизайна. Это ещё одно преимущество DI: оно часто документирует намерения. Когда вы полагаетесь на глобальные переменные, обязанности становятся очень нечёткими.

## Пример функции, реализующей интерфейс

Когда вы определяете интерфейс с одним методом, вы можете рассмотреть возможность определения типа `MyInterfaceFunc` в дополнение к нему, чтобы пользователи могли реализовать ваш интерфейс просто с помощью функции.

```go
type BlindAlerter interface {
	ScheduleAlertAt(duration time.Duration, amount int)
}

// BlindAlerterFunc allows you to implement BlindAlerter with a function
type BlindAlerterFunc func(duration time.Duration, amount int)

// ScheduleAlertAt is BlindAlerterFunc implementation of BlindAlerter
func (a BlindAlerterFunc) ScheduleAlertAt(duration time.Duration, amount int) {
	a(duration, amount)
}
```

Делая это, пользователи вашей библиотеки могут реализовать ваш интерфейс с помощью всего лишь функции. Они могут использовать [преобразование типов](https://go.dev/tour/basics/13), чтобы преобразовать свою функцию в `BlindAlerterFunc`, а затем использовать её как `BlindAlerter` (поскольку `BlindAlerterFunc` реализует `BlindAlerter`).

```go
game := poker.NewTexasHoldem(poker.BlindAlerterFunc(poker.StdOutAlerter), store)
```

Более широкий смысл здесь заключается в том, что в Go вы можете добавлять методы к _типам_, а не только к структурам. Это очень мощная функция, и вы можете использовать её для более удобной реализации интерфейсов.

Учтите, что вы можете не только определять типы функций, но и определять типы вокруг других типов, чтобы добавлять к ним методы.

```go
type Blog map[string]string

func (b Blog) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintln(w, b[r.URL.Path])
}
```

Здесь мы создали HTTP-обработчик, который реализует очень простой "блог", где он будет использовать пути URL в качестве ключей к записям, хранящимся в `map`.
