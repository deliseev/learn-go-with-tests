---
# Конкурентность

**[Весь код для этой главы вы найдете здесь](https://github.com/quii/learn-go-with-tests/tree/main/concurrency)**

Вот начальные условия: коллега написал функцию `CheckWebsites`, которая
проверяет статус списка URL-адресов.

```go
package concurrency

type WebsiteChecker func(string) bool

func CheckWebsites(wc WebsiteChecker, urls []string) map[string]bool {
	results := make(map[string]bool)

	for _, url := range urls {
		results[url] = wc(url)
	}

	return results
}
```

Она возвращает `map` (карту) каждого проверенного URL-адреса с логическим значением: `true` для хорошего ответа; `false` для плохого ответа.

Вы также должны передать `WebsiteChecker`, который принимает один URL-адрес и возвращает
логическое значение. Он используется функцией для проверки всех веб-сайтов.

Использование [внедрения зависимостей][DI] позволило им протестировать функцию без
выполнения реальных HTTP-вызовов, что сделало ее надежной и быстрой.

Вот тест, который они написали:

```go
package concurrency

import (
	"reflect"
	"testing"
)

func mockWebsiteChecker(url string) bool {
	return url != "waat://furhurterwe.geds"
}

func TestCheckWebsites(t *testing.T) {
	websites := []string{
		"http://google.com",
		"http://blog.gypsydave5.com",
		"waat://furhurterwe.geds",
	}

	want := map[string]bool{
		"http://google.com":          true,
		"http://blog.gypsydave5.com": true,
		"waat://furhurterwe.geds":    false,
	}

	got := CheckWebsites(mockWebsiteChecker, websites)

	if !reflect.DeepEqual(want, got) {
		t.Fatalf("wanted %v, got %v", want, got)
	}
}
```

Функция находится в продакшене и используется для проверки сотен веб-сайтов. Но
ваш коллега начал получать жалобы на то, что она работает медленно, поэтому он попросил
вас помочь ускорить ее.

## Напишем тест

Давайте используем бенчмарк, чтобы проверить скорость `CheckWebsites` и увидеть
эффект от наших изменений.

```go
package concurrency

import (
	"testing"
	"time"
)

func slowStubWebsiteChecker(_ string) bool {
	time.Sleep(20 * time.Millisecond)
	return true
}

func BenchmarkCheckWebsites(b *testing.B) {
	urls := make([]string, 100)
	for i := 0; i < len(urls); i++ {
		urls[i] = "a url"
	}

	for b.Loop() {
		CheckWebsites(slowStubWebsiteChecker, urls)
	}
}
```

Бенчмарк тестирует `CheckWebsites`, используя срез из ста URL-адресов, и новую
фейковую реализацию `WebsiteChecker`. `slowStubWebsiteChecker` намеренно замедлена.
Она использует `time.Sleep` для ожидания ровно двадцати миллисекунд, а затем
возвращает `true`.

Когда мы запускаем бенчмарк с помощью `go test -bench=.` (или, если вы используете Windows Powershell, `go test -bench="."`):

```sh
pkg: github.com/gypsydave5/learn-go-with-tests/concurrency/v0
BenchmarkCheckWebsites-4               1        2249228637 ns/op
PASS
ok      github.com/gypsydave5/learn-go-with-tests/concurrency/v0        2.268s
```

Бенчмарк показал, что `CheckWebsites` выполняется за 2249228637 наносекунд —
примерно за две с четвертью секунды.

Давайте попробуем ускорить это.

### Напишите достаточно кода, чтобы он прошел

Теперь мы наконец можем поговорить о конкурентности (concurrency), которая, для
целей следующего, означает "выполнение нескольких дел одновременно". Это то, что
мы делаем естественно каждый день.

Например, сегодня утром я приготовил чашку чая. Я поставил чайник и затем, пока
ждал, когда он закипит, достал молоко из холодильника, взял чай из шкафа, нашел
свою любимую кружку, положил чайный пакетик в чашку, а затем, когда чайник
закипел, налил воду в чашку.

Чего я _не_ делал, так это не ставил чайник, а затем тупо стоял и смотрел на
него, пока он не закипит, и только потом делал все остальное.

Если вы понимаете, почему первый способ приготовления чая быстрее, то вы поймете,
как мы ускорим `CheckWebsites`. Вместо того чтобы ждать ответа от одного
веб-сайта, прежде чем отправить запрос к следующему, мы скажем нашему компьютеру
сделать следующий запрос, пока он ждет.

Обычно в Go, когда мы вызываем функцию `doSomething()`, мы ждем, пока она
вернется (даже если ей нечего возвращать, мы все равно ждем ее завершения). Мы
говорим, что эта операция является *блокирующей* — она заставляет нас ждать ее
завершения. Операция, которая не блокирует в Go, будет выполняться в отдельном
*процессе*, называемом *горутиной* (goroutine). Представьте себе процесс как
чтение страницы кода Go сверху вниз, заходя 'внутрь' каждой функции при ее вызове,
чтобы прочитать, что она делает. Когда начинается отдельный процесс, это похоже на
то, как другой читатель начинает читать внутри функции, оставляя первоначального
читателя продолжать идти вниз по странице.

Чтобы сообщить Go о запуске новой горутины, мы превращаем вызов функции в оператор
`go`, помещая перед ним ключевое слово `go`: `go doSomething()`.

```go
package concurrency

type WebsiteChecker func(string) bool

func CheckWebsites(wc WebsiteChecker, urls []string) map[string]bool {
	results := make(map[string]bool)

	for _, url := range urls {
		go func() {
			results[url] = wc(url)
		}()
	}

	return results
}
```

Поскольку единственный способ запустить горутину — это поставить `go` перед
вызовом функции, мы часто используем *анонимные функции* (anonymous functions),
когда хотим запустить горутину. Анонимный функциональный литерал выглядит так
же, как обычное объявление функции, но без имени (что неудивительно). Вы можете
увидеть его выше в теле цикла `for`.

Анонимные функции обладают рядом особенностей, которые делают их полезными, две
из которых мы используем выше. Во-первых, они могут быть выполнены одновременно с
их объявлением — это то, что делают `()` в конце анонимной функции. Во-вторых,
они сохраняют доступ к лексической области видимости, в которой они определены —
все переменные, доступные в точке объявления анонимной функции, также доступны
в теле функции.

Тело анонимной функции выше такое же, как и было тело цикла раньше. Единственное
отличие состоит в том, что каждая итерация цикла будет запускать новую горутину,
работающую конкурентно с текущим процессом (функцией `WebsiteChecker`). Каждая
горутина будет добавлять свой результат в `map` `results`.

Но когда мы запускаем `go test`:

```sh
--- FAIL: TestCheckWebsites (0.00s)
        CheckWebsites_test.go:31: Wanted map[http://google.com:true http://blog.gypsydave5.com:true waat://furhurterwe.geds:false], got map[]
FAIL
exit status 1
FAIL    github.com/gypsydave5/learn-go-with-tests/concurrency/v1        0.010s
```

### Краткое отступление в мир конкурентности...

Вы можете не получить этот результат. Вы можете получить сообщение о панике, о
котором мы поговорим чуть позже. Не волнуйтесь, если вы его получили, просто
продолжайте запускать тест, пока _не_ получите результат, показанный выше. Или
притворитесь, что получили. Решать вам. Добро пожаловать в мир конкурентности:
когда она неправильно обрабатывается, трудно предсказать, что произойдет. Не
волнуйтесь — именно поэтому мы пишем тесты, чтобы помочь нам узнать, когда мы
обрабатываем конкурентность предсказуемо.

### ... и мы вернулись.

Мы столкнулись с проблемой в исходном тесте `CheckWebsites`: теперь он возвращает
пустую карту. Что пошло не так?

Ни одна из горутин, запущенных нашим циклом `for`, не успела добавить свой
результат в `map` `results`; функция `CheckWebsites` слишком быстра для них,
и она возвращает все еще пустую карту.

Чтобы исправить это, мы можем просто подождать, пока все горутины выполнят свою
работу, а затем вернуть результат. Двух секунд должно хватить, верно?

```go
package concurrency

import "time"

type WebsiteChecker func(string) bool

func CheckWebsites(wc WebsiteChecker, urls []string) map[string]bool {
	results := make(map[string]bool)

	for _, url := range urls {
		go func() {
			results[url] = wc(url)
		}()
	}

	time.Sleep(2 * time.Second)

	return results
}
```

Теперь, если вам повезет, вы получите:

```sh
PASS
ok      github.com/gypsydave5/learn-go-with-tests/concurrency/v1        2.012s
```

Но если вам не повезет (это более вероятно, если вы запустите их с бенчмарком, так как у вас будет больше попыток)

```sh
fatal error: concurrent map writes

goroutine 8 [running]:
runtime.throw(0x12c5895, 0x15)
        /usr/local/Cellar/go/1.9.3/libexec/src/runtime/panic.go:605 +0x95 fp=0xc420037700 sp=0xc4200376e0 pc=0x102d395
runtime.mapassign_faststr(0x1271d80, 0xc42007acf0, 0x12c6634, 0x17, 0x0)
        /usr/local/Cellar/go/1.9.3/libexec/src/runtime/hashmap_fast.go:783 +0x4f5 fp=0xc420037780 sp=0xc420037700 pc=0x100eb65
github.com/gypsydave5/learn-go-with-tests/concurrency/v3.WebsiteChecker.func1(0xc42007acf0, 0x12d3938, 0x12c6634, 0x17)
        /Users/gypsydave5/go/src/github.com/gypsydave5/learn-go-with-tests/concurrency/v3/websiteChecker.go:12 +0x71 fp=0xc4200377c0 sp=0xc420037780 pc=0x12308f1
runtime.goexit()
        /usr/local/Cellar/go/1.9.3/libexec/src/runtime/asm_amd64.s:2337 +0x1 fp=0xc4200377c8 sp=0xc4200377c0 pc=0x105cf01
created by github.com/gypsydave5/learn-go-with-tests/concurrency/v3.WebsiteChecker
        /Users/gypsydave5/go/src/github.com/gypsydave5/learn-go-with-tests/concurrency/v3/websiteChecker.go:11 +0xa1

        ... many more scary lines of text ...
```

Это длинно и страшно, но все, что нам нужно сделать, это перевести дух и прочитать
трассировку стека: `fatal error: concurrent map writes`. Иногда, когда мы
запускаем наши тесты, две горутины записывают данные в `map` `results` в одно и
то же время. Карты в Go не любят, когда более одной сущности пытается записывать
в них данные одновременно, и поэтому возникает `fatal error`.

Это _состояние гонки данных_ (data race) — ошибка, которая возникает, когда две
или более горутины одновременно обращаются к одной и той же области памяти,
и хотя бы один из этих доступов является записью. Поскольку мы не можем точно
контролировать, когда каждая горутина выполнится, мы уязвимы к тому, что несколько
горутин попытаются записать данные в `map` `results` в одно и то же время. Карты
Go не являются безопасными для конкурентных записей, поэтому среда выполнения
выдает фатальную ошибку, чтобы предотвратить повреждение памяти.

Go может помочь нам выявить состояния гонки с помощью встроенного
[_детектора гонок_][godoc_race_detector]. Чтобы включить эту функцию, запустите
тесты с флагом `race`: `go test -race`.

Вы должны получить вывод, который выглядит примерно так:

```sh
==================
WARNING: DATA RACE
Write at 0x00c420084d20 by goroutine 8:
  runtime.mapassign_faststr()
      /usr/local/Cellar/go/1.9.3/libexec/src/runtime/hashmap_fast.go:774 +0x0
  github.com/gypsydave5/learn-go-with-tests/concurrency/v3.WebsiteChecker.func1()
      /Users/gypsydave5/go/src/github.com/gypsydave5/learn-go-with-tests/concurrency/v3/websiteChecker.go:12 +0x82

Previous write at 0x00c420084d20 by goroutine 7:
  runtime.mapassign_faststr()
      /usr/local/Cellar/go/1.9.3/libexec/src/runtime/hashmap_fast.go:774 +0x0
  github.com/gypsydave5/learn-go-with-tests/concurrency/v3.WebsiteChecker.func1()
      /Users/gypsydave5/go/src/github.com/gypsydave5/learn-go-with-tests/concurrency/v3/websiteChecker.go:12 +0x82

Goroutine 8 (running) created at:
  github.com/gypsydave5/learn-go-with-tests/concurrency/v3.WebsiteChecker()
      /Users/gypsydave5/go/src/github.com/gypsydave5/learn-go-with-tests/concurrency/v3/websiteChecker.go:11 +0xc4
  github.com/gypsydave5/learn-go-with-tests/concurrency/v3.TestWebsiteChecker()
      /Users/gypsydave5/go/src/github.com/gypsydave5/learn-go-with-tests/concurrency/v3/websiteChecker_test.go:27 +0xad
  testing.tRunner()
      /usr/local/Cellar/go/1.9.3/libexec/src/testing/testing.go:746 +0x16c

Goroutine 7 (finished) created at:
  github.com/gypsydave5/learn-go-with-tests/concurrency/v3.WebsiteChecker()
      /Users/gypsydave5/go/src/github.com/gypsydave5/learn-go-with-tests/concurrency/v3/websiteChecker.go:11 +0xc4
  github.com/gypsydave5/learn-go-with-tests/concurrency/v3.TestWebsiteChecker()
      /Users/gypsydave5/go/src/github.com/gypsydave5/learn-go-with-tests/concurrency/v3/websiteChecker_test.go:27 +0xad
  testing.tRunner()
      /usr/local/Cellar/go/1.9.3/libexec/src/testing/testing.go:746 +0x16c
==================
```

Детали, опять же, трудно читать — но `WARNING: DATA RACE` довольно однозначно.
Вчитываясь в тело ошибки, мы видим две разные горутины, выполняющие записи в карту:

`Write at 0x00c420084d20 by goroutine 8:`

записывает в тот же блок памяти, что и

`Previous write at 0x00c420084d20 by goroutine 7:`

Вдобавок, мы можем увидеть строку кода, где происходит запись:

`/Users/gypsydave5/go/src/github.com/gypsydave5/learn-go-with-tests/concurrency/v3/websiteChecker.go:12`

и строку кода, где запущены горутины 7 и 8:

`/Users/gypsydave5/go/src/github.com/gypsydave5/learn-go-with-tests/concurrency/v3/websiteChecker.go:11`

Все, что вам нужно знать, выведено в ваш терминал — все, что вам нужно сделать,
это набраться терпения, чтобы прочитать это.

### Каналы

Мы можем решить эту проблему состояния гонки данных, координируя наши горутины
с помощью _каналов_ (channels). Каналы — это структура данных Go, которая может
как принимать, так и отправлять значения. Эти операции, наряду с их деталями,
позволяют обмениваться данными между различными процессами.

В данном случае мы хотим подумать о связи между родительским процессом и каждой
из горутин, которые он создает для выполнения работы функции `WebsiteChecker`
с URL-адресом.

```go
package concurrency

type WebsiteChecker func(string) bool
type result struct {
	string
	bool
}

func CheckWebsites(wc WebsiteChecker, urls []string) map[string]bool {
	results := make(map[string]bool)
	resultChannel := make(chan result)

	for _, url := range urls {
		go func() {
			resultChannel <- result{url, wc(url)}
		}()
	}

	for i := 0; i < len(urls); i++ {
		r := <-resultChannel
		results[r.string] = r.bool
	}

	return results
}
```

> **Замечание о `url` внутри горутины.** Каждая итерация цикла запускает новую горутину, ссылающуюся на `url`, без явной его передачи. Начиная с Go 1.22, это безопасно: спецификация языка была изменена так, что `url` является новой переменной на каждой итерации, поэтому каждая горутина захватывает свою собственную копию.
>
> Если вы запустите это в проекте, чей `go.mod` объявляет версию `go` *старше* `1.22`, вы вместо этого получите старое поведение: `url` будет единственной переменной, разделяемой и повторно используемой каждой итерацией, так что к моменту выполнения горутин они, скорее всего, все увидят одно и то же (вероятно, конечное) значение `url`. Это сбивает с толку, потому что ваш _набор инструментов Go_ (`toolchain`) может быть новым, в то время как директива `go` в вашем `go.mod` старая — набор инструментов учитывает ту семантику переменной цикла, которую подразумевает объявленная версия. Исправление для старой версии `go.mod` состоит в явной передаче `url` в горутину: `go func(url string) { ... }(url)`.

Наряду с `map` `results` у нас теперь есть `resultChannel`, который мы создаем
с помощью `make` таким же образом. `chan result` — это тип канала — канал
`result`. Новый тип `result` был создан для связывания возвращаемого значения
`WebsiteChecker` с проверяемым URL-адресом — это структура (`struct`) из `string`
и `bool`. Поскольку нам не нужно называть ни одно из значений, каждое из них
является анонимным внутри структуры; это может быть полезно, когда трудно
придумать имя для значения.

Теперь, когда мы итерируем по URL-адресам, вместо прямой записи в `map` мы
отправляем структуру `result` для каждого вызова `wc` в `resultChannel` с
помощью _оператора отправки_ (send statement). Он использует оператор `<-`,
принимая канал слева и значение справа:

```go
// Оператор отправки
resultChannel <- result{url, wc(url)}
```

Следующий цикл `for` итерируется один раз для каждого из URL-адресов. Внутри мы
используем _выражение получения_ (receive expression), которое присваивает значение,
полученное из канала, переменной. Оно также использует оператор `<-`, но с
обратными операндами: канал теперь находится справа, а переменная, которой мы
присваиваем значение, находится слева:

```go
// Выражение получения
r := <-resultChannel
```

Затем мы используем полученный `result` для обновления карты.

Отправляя результаты в канал, мы можем контролировать время каждой записи в
`map` `results`, гарантируя, что это происходит поочередно. Хотя каждый из
вызовов `wc` и каждая отправка в канал результатов происходят конкурентно
внутри своего собственного процесса, каждый из результатов обрабатывается по
одному, когда мы извлекаем значения из канала результатов с помощью выражения
получения.

Мы использовали конкурентность для той части кода, которую хотели ускорить, при
этом убедившись, что часть, которая не может выполняться одновременно, все еще
выполняется линейно. И мы осуществляли связь между множеством задействованных
процессов с помощью каналов.

Когда мы запускаем бенчмарк:

```sh
pkg: github.com/gypsydave5/learn-go-with-tests/concurrency/v2
BenchmarkCheckWebsites-8             100          23406615 ns/op
PASS
ok      github.com/gypsydave5/learn-go-with-tests/concurrency/v2        2.377s
```
23406615 наносекунд — 0.023 секунды, примерно в сто раз быстрее исходной функции. Большой успех.

## Подведение итогов

Это упражнение было немного менее сфокусировано на TDD, чем обычно. В некотором
смысле, мы участвовали в длительном рефакторинге функции `CheckWebsites`;
входные и выходные данные никогда не менялись, она просто стала быстрее. Но
имеющиеся у нас тесты, а также написанный нами бенчмарк, позволили нам
рефакторить `CheckWebsites` таким образом, чтобы сохранить уверенность в том,
что программное обеспечение по-прежнему работает, одновременно демонстрируя,
что оно действительно стало быстрее.

Ускоряя код, мы узнали о:

*   *горутинах* (goroutines) — базовой единице конкурентности в Go, которая
    позволяет нам управлять более чем одним запросом на проверку веб-сайта.
*   *анонимных функциях* (anonymous functions), которые мы использовали для
    запуска каждого из конкурентных процессов, проверяющих веб-сайты.
*   *каналах* (channels), которые помогают организовывать и контролировать связь
    между различными процессами, позволяя нам избежать ошибки *состояния гонки*
    (race condition).
*   *детекторе гонок* (race detector), который помог нам отлаживать проблемы с
    конкурентным кодом.

### Сделаем это быстро

Одна из формулировок гибкого подхода к разработке программного обеспечения,
часто ошибочно приписываемая Кенту Беку, звучит так:

> [Заставь работать, сделай правильно, сделай быстро][wrf]

Где «работать» означает заставить тесты проходить, «правильно» — это рефакторинг
кода, а «быстро» — это оптимизация кода, чтобы, например, он выполнялся быстро.
Мы можем «сделать быстро» только после того, как мы заставили его работать и
сделали его правильным. Нам повезло, что предоставленный нам код уже был
продемонстрирован как работающий и не требовал рефакторинга. Мы никогда не
должны пытаться «сделать быстро» до того, как будут выполнены два других шага,
потому что

> [Преждевременная оптимизация — корень всех зол][popt]
> -- Дональд Кнут

[DI]: dependency-injection.md
[wrf]: http://wiki.c2.com/?MakeItWorkMakeItRightMakeItFast
[godoc_race_detector]: https://blog.golang.org/race-detector
[popt]: http://wiki.c2.com/?PrematureOptimization
---