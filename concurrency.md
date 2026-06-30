# Конкурентность

**[Весь код для этой главы вы можете найти здесь](https://github.com/quii/learn-go-with-tests/tree/main/concurrency)**

Начальная ситуация: коллега написал функцию `CheckWebsites`, которая
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

Она возвращает отображение каждого проверенного URL-адреса с булевым значением: `true` для
хорошего ответа; `false` для плохого ответа.

В функцию также необходимо передать `WebsiteChecker`, который принимает один URL-адрес и возвращает
булево значение. Это используется функцией для проверки всех веб-сайтов.

Использование [внедрения зависимостей][DI] позволило им протестировать функцию
без выполнения реальных HTTP-вызовов, что делает её надежной и быстрой.

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
ваш коллега начал получать жалобы на медленную работу, поэтому он
попросил вас помочь ускорить её.

## Напишите тест

Давайте используем бенчмарк для проверки скорости работы `CheckWebsites`, чтобы
увидеть эффект от наших изменений.

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

Бенчмарк тестирует `CheckWebsites`, используя срез из ста URL-адресов и
новую фейковую реализацию `WebsiteChecker`. `slowStubWebsiteChecker`
намеренно медленный. Он использует `time.Sleep`, чтобы ждать ровно двадцать
миллисекунд, а затем возвращает `true`.

Когда мы запускаем бенчмарк с помощью `go test -bench=.` (или в Windows Powershell `go test -bench="."`):

```sh
pkg: github.com/gypsydave5/learn-go-with-tests/concurrency/v0
BenchmarkCheckWebsites-4               1        2249228637 ns/op
PASS
ok      github.com/gypsydave5/learn-go-with-tests/concurrency/v0        2.268s
```

Производительность `CheckWebsites` была измерена в 2249228637 наносекунд — около двух с
четвертью секунд.

Давайте попробуем ускорить это.

### Напишите достаточно кода, чтобы он прошел

Теперь мы наконец можем поговорить о конкурентности, которая для целей
следующего означает "наличие нескольких выполняющихся задач одновременно". Это
то, что мы делаем естественным образом каждый день.

Например, сегодня утром я приготовил чашку чая. Я поставил чайник, а затем,
пока он закипал, достал молоко из холодильника, достал чай из шкафа,
нашел свою любимую кружку, положил чайный пакетик в чашку, а затем,
когда чайник закипел, налил воду в чашку.

Чего я _не_ делал, так это не ставил чайник, а потом тупо стоял и смотрел на
него, пока он не закипел, а затем делал всё остальное.

Если вы понимаете, почему первый способ заваривания чая быстрее, то вы
поймете, как мы ускорим `CheckWebsites`. Вместо того чтобы ждать ответа
от одного веб-сайта, прежде чем отправить запрос к следующему, мы скажем
нашему компьютеру сделать следующий запрос, пока он ждёт.

Обычно в Go, когда мы вызываем функцию `doSomething()`, мы ждём, пока она вернётся
(даже если она не возвращает значение, мы всё равно ждём её завершения). Мы говорим, что
эта операция *блокирующая* — она заставляет нас ждать ее завершения. Операция, которая
не блокирует в Go, будет выполняться в отдельном *процессе*, называемом
*горутиной*. Представьте процесс как чтение кода Go сверху вниз,
заходя 'внутрь' каждой функции при ее вызове, чтобы прочитать, что она делает.
Когда запускается отдельный процесс, это похоже на то, как другой 'читатель' начинает
читать внутри функции, позволяя первоначальному 'читателю' продолжать
двигаться по странице вниз.

Чтобы сообщить Go о запуске новой горутины, мы превращаем вызов функции в
`go`-оператор, поставив ключевое слово `go` перед ним: `go doSomething()`.

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
вызовом функции, мы часто используем *анонимные функции*, когда хотим запустить
горутину. Литерал анонимной функции выглядит так же, как обычное объявление
функции, но без имени (что неудивительно). Вы можете увидеть одну выше в теле
цикла `for`.

Анонимные функции обладают рядом полезных особенностей, две из которых мы
используем выше. Во-первых, они могут быть выполнены одновременно с их
объявлением — это то, что делает `()` в конце анонимной функции. Во-вторых,
они сохраняют доступ к лексическому окружению, в котором они определены — все
переменные, доступные в момент объявления анонимной функции, также доступны в
теле функции.

Тело анонимной функции выше точно такое же, как и тело цикла ранее.
Единственная разница в том, что каждая итерация цикла будет запускать новую
горутину, конкурентно с текущим процессом (функцией `WebsiteChecker`). Каждая
горутина добавит свой результат в отображение `results`.

Но когда мы запускаем `go test`:

```sh
--- FAIL: TestCheckWebsites (0.00s)
        CheckWebsites_test.go:31: Wanted map[http://google.com:true http://blog.gypsydave5.com:true waat://furhurterwe.geds:false], got map[]
FAIL
exit status 1
FAIL    github.com/gypsydave5/learn-go-with-tests/concurrency/v1        0.010s

```

### Небольшое отступление в мир конкурентности...

Вы можете не получить этот результат. Вы можете получить сообщение о панике, о
котором мы поговорим чуть позже. Не беспокойтесь, если вы его получили, просто
продолжайте запускать тест, пока не получите результат, показанный выше. Или
притворитесь, что получили. Решать вам. Добро пожаловать в мир конкурентности:
если она не обрабатывается правильно, трудно предсказать, что произойдет. Не
беспокойтесь — именно поэтому мы пишем тесты, чтобы помочь нам узнать, когда мы
обрабатываем конкурентность предсказуемо.

### ... и мы снова здесь.

Нас поймал исходный тест `CheckWebsites`, теперь он возвращает пустое отображение. Что пошло не так?

Ни одна из горутин, запущенных нашим циклом `for`, не успела добавить свой
результат в отображение `results`; функция `CheckWebsites` слишком быстра для них, и
она возвращает всё еще пустое отображение.

Чтобы исправить это, мы можем просто подождать, пока все горутины выполнят свою
работу, а затем вернуть результат. Две секунды должно хватить, верно?

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

Но если вам не повезёт (это более вероятно, если вы запустите их с бенчмарком, так как у вас будет больше попыток)

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

Это длинное и страшное сообщение, но всё, что нам нужно сделать, это перевести
дух и прочитать трассировку стека: `fatal error: concurrent map writes`. Иногда,
когда мы запускаем наши тесты, две горутины одновременно записывают данные в
`results`. Отображения в Go не любят, когда более одной сущности пытаются
записать в них данные одновременно, и поэтому возникает `fatal error`.

Это _состояние гонки данных_ (data race), ошибка, которая возникает, когда две или
более горутины обращаются к одному и тому же участку памяти одновременно, и по
крайней мере одно из этих обращений является записью. Поскольку мы не можем
точно контролировать, когда каждая горутина выполняется, мы уязвимы перед
ситуацией, когда несколько горутин пытаются записать данные в `results`
одновременно. Отображение Go не являются безопасными для конкурентной записи, поэтому
среда выполнения выбрасывает фатальную ошибку, чтобы предотвратить повреждение
памяти.

Go может помочь нам обнаруживать состояния гонки с помощью встроенного
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

Детали, опять же, трудно читаемы, но `WARNING: DATA RACE` довольно однозначно.
Вникая в тело ошибки, мы видим две разные горутины, выполняющие запись в отображение:

`Write at 0x00c420084d20 by goroutine 8:`

записывает в тот же блок памяти, что и

`Previous write at 0x00c420084d20 by goroutine 7:`

Помимо этого, мы можем увидеть строку кода, где происходит запись:

`/Users/gypsydave5/go/src/github.com/gypsydave5/learn-go-with-tests/concurrency/v3/websiteChecker.go:12`

и строку кода, где горутины 7 и 8 были запущены:

`/Users/gypsydave5/go/src/github.com/gypsydave5/learn-go-with-tests/concurrency/v3/websiteChecker.go:11`

Всё, что вам нужно знать, выводится в ваш терминал — всё, что вам нужно
сделать, это быть достаточно терпеливым, чтобы прочитать это.

### Каналы

Мы можем решить это состояние гонки данных, координируя наши горутины с помощью
_каналов_. Каналы — это структура данных Go, которая может как получать, так и
отправлять значения. Эти операции, наряду с их деталями, позволяют
осуществлять связь между различными процессами.

В данном случае мы хотим подумать о связи между родительским процессом и каждой
из горутин, которые он создает для выполнения работы по запуску функции
`WebsiteChecker` с URL-адресом.

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

Наряду с отображением `results` теперь у нас есть `resultChannel`, который мы
`make`'им таким же образом. `chan result` — это тип канала — канал `result`.
Новый тип `result` был создан для связывания возвращаемого значения
`WebsiteChecker` с проверяемым URL-адресом — это структура из `string` и
`bool`. Поскольку нам не нужно давать имена ни одному из значений, каждое из
них анонимно внутри структуры; это может быть полезно, когда трудно придумать
имя для значения.

Теперь, когда мы итерируем по URL-адресам, вместо прямой записи в `map` мы
отправляем структуру `result` для каждого вызова `wc` в `resultChannel` с
помощью _оператора отправки_. Он использует оператор `<-`, принимая канал
слева и значение справа:

```go
// Send statement
resultChannel <- result{url, wc(url)}
```

Следующий цикл `for` итерируется один раз для каждого из URL-адресов. Внутри
мы используем _выражение получения_, которое присваивает значение, полученное
из канала, переменной. Оно также использует оператор `<-`, но с двумя
операндами, теперь поменянными местами: канал теперь справа, а переменная,
которой мы присваиваем значение, слева:

```go
// Receive expression
r := <-resultChannel
```

Затем мы используем полученный `result` для обновления отображения.

Отправляя результаты в канал, мы можем контролировать время каждой записи в
отображение результатов, гарантируя, что это происходит по очереди. Хотя каждый
вызов `wc` и каждая отправка в канал результатов происходят конкурентно внутри
собственного процесса, каждый из результатов обрабатывается по одному, когда мы
извлекаем значения из канала результатов с помощью выражения получения.

Мы использовали конкурентность для той части кода, которую хотели ускорить, при
этом убедившись, что часть, которая не может выполняться одновременно, всё еще
выполняется линейно. И мы обеспечили связь между множеством задействованных
процессов, используя каналы.

Когда мы запускаем бенчмарк:

```sh
pkg: github.com/gypsydave5/learn-go-with-tests/concurrency/v2
BenchmarkCheckWebsites-8             100          23406615 ns/op
PASS
ok      github.com/gypsydave5/learn-go-with-tests/concurrency/v2        2.377s
```
23406615 наносекунд — 0.023 секунды, примерно в сто раз быстрее исходной
функции. Отличный успех.

## Итоги

Это упражнение было немного менее ориентированным на TDD, чем обычно. В
некотором смысле мы участвовали в длительном рефакторинге функции
`CheckWebsites`; входы и выходы никогда не менялись, она просто стала быстрее.
Но имеющиеся у нас тесты, а также написанный нами бенчмарк, позволили нам
провести рефакторинг `CheckWebsites` таким образом, чтобы сохранить уверенность
в работоспособности ПО, одновременно демонстрируя, что оно действительно стало
быстрее.

Ускоряя его, мы узнали о:

-   *горутинах*, базовой единице конкурентности в Go, которые позволяют нам
    управлять несколькими запросами на проверку веб-сайтов.
-   *анонимных функциях*, которые мы использовали для запуска каждого из
    конкурентных процессов, проверяющих веб-сайты.
-   *каналах*, помогающих организовать и контролировать связь между различными
    процессами, что позволяет избежать ошибки *состояния гонки*.
-   *детекторе гонок*, который помог нам отлаживать проблемы с конкурентным
    кодом.

### Сделай это быстрым

Одна из формулировок гибкого подхода к разработке ПО, часто ошибочно
приписываемая Кенту Беку, звучит так:

[Заставь работать, сделай правильно, сделай быстро][wrf]

Где 'работать' — это добиться прохождения тестов, 'правильно' — это рефакторинг
кода, а 'быстро' — это оптимизация кода, чтобы он, например, работал быстро. Мы
можем 'сделать это быстрым' только после того, как заставим его работать и
сделаем его правильным. Нам повезло, что предоставленный нам код уже был
продемонстрирован как рабочий и не требовал рефакторинга. Мы никогда не должны
пытаться 'сделать это быстрым' до того, как будут выполнены два других шага,
потому что

[Преждевременная оптимизация — корень всех зол][popt]
-- Дональд Кнут

[DI]: dependency-injection.md
[wrf]: http://wiki.c2.com/?MakeItWorkMakeItRightMakeItFast
[godoc_race_detector]: https://blog.golang.org/race-detector
[popt]: http://wiki.c2.com/?PrematureOptimization