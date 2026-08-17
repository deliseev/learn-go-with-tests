# Конкурентность

**[Весь код для этой главы вы найдете здесь](https://github.com/quii/learn-go-with-tests/tree/main/concurrency)**

Итак, имеется следующая ситуация: коллега написал функцию `CheckWebsites`, которая проверяет статус списка URL-адресов.

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

Она возвращает карту, в которой каждому проверенному URL-адресу соответствует булево значение: `true` для успешного ответа; `false` для неуспешного.

Также необходимо передать `WebsiteChecker`, которая принимает один URL-адрес и возвращает булево значение. Эта функция используется для проверки всех веб-сайтов.

Использование [внедрения зависимостей][DI] позволило им тестировать функцию без выполнения реальных HTTP-запросов, делая ее надежной и быстрой.

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

Функция находится в продакшене и используется для проверки сотен веб-сайтов. Но ваш коллега начал получать жалобы на ее медленную работу, поэтому он попросил вас помочь ускорить ее.

## Напишем тест

Давайте используем бенчмарк (тест производительности), чтобы проверить скорость `CheckWebsites` и увидеть эффект от наших изменений.

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

Бенчмарк тестирует `CheckWebsites`, используя срез из ста URL-адресов, и новую фейковую реализацию `WebsiteChecker`. `slowStubWebsiteChecker` намеренно медленная. Она использует `time.Sleep`, чтобы ждать ровно двадцать миллисекунд, а затем возвращает `true`.

Когда мы запускаем бенчмарк с помощью `go test -bench=.` (или, если вы используете Windows Powershell, `go test -bench="."`):

```sh
pkg: github.com/gypsydave5/learn-go-with-tests/concurrency/v0
BenchmarkCheckWebsites-4               1        2249228637 ns/op
PASS
ok      github.com/gypsydave5/learn-go-with-tests/concurrency/v0        2.268s
```

`CheckWebsites` показала результат в 2249228637 наносекунд — около двух с четвертью секунд.

Попробуем сделать это быстрее.

### Напишем достаточно кода, чтобы тест прошел

Теперь мы наконец можем поговорить о параллелизме (concurrency), который для целей следующего изложения означает "наличие более чем одного процесса в работе". Это то, что мы естественно делаем каждый день.

Например, этим утром я приготовил чашку чая. Я поставил чайник и затем, пока ждал его закипания, достал молоко из холодильника, взял чай из шкафа, нашел свою любимую кружку, положил чайный пакетик в чашку, а затем, когда чайник закипел, налил воду в чашку.

Чего я *не* делал, так это не ставил чайник, а потом не стоял, тупо глядя на него, пока он не закипит, чтобы потом сделать все остальное.

Если вы понимаете, почему быстрее заваривать чай первым способом, то вы поймете, как мы ускорим `CheckWebsites`. Вместо того чтобы ждать ответа от одного веб-сайта, прежде чем отправлять запрос к следующему, мы укажем нашему компьютеру сделать следующий запрос, пока он ждет.

Обычно в Go, когда мы вызываем функцию `doSomething()`, мы ждем ее возврата (даже если ей нечего возвращать, мы все равно ждем ее завершения). Мы говорим, что эта операция *блокирующая* — она заставляет нас ждать ее завершения. Операция, которая не блокирует в Go, будет выполняться в отдельном *процессе*, называемом *горутиной*. Представьте процесс как чтение страницы Go-кода сверху вниз, "заходя" внутрь каждой функции при ее вызове, чтобы прочитать, что она делает. Когда начинается отдельный процесс, это похоже на то, как другой читатель начинает читать внутри функции, позволяя первоначальному читателю продолжать двигаться по странице.

Чтобы указать Go запустить новую горутину, мы превращаем вызов функции в `go`-оператор, помещая ключевое слово `go` перед ним: `go doSomething()`.

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

Поскольку единственный способ запустить горутину — это поместить `go` перед вызовом функции, мы часто используем *анонимные функции*, когда хотим запустить горутину. Литерал анонимной функции выглядит так же, как обычное объявление функции, но без имени (что неудивительно). Вы можете увидеть такую выше в теле цикла `for`.

Анонимные функции обладают рядом особенностей, которые делают их полезными, две из которых мы используем выше. Во-первых, они могут быть выполнены одновременно с их объявлением — это то, что делает `()` в конце анонимной функции. Во-вторых, они сохраняют доступ к лексической области видимости, в которой они определены — все переменные, доступные в точке объявления анонимной функции, также доступны в теле функции.

Тело анонимной функции выше точно такое же, как и тело цикла ранее. Единственная разница заключается в том, что каждая итерация цикла будет запускать новую горутину, параллельно с текущим процессом (функцией `WebsiteChecker`). Каждая горутина будет добавлять свой результат в карту `results`.

Но когда мы запускаем `go test`:

```sh
--- FAIL: TestCheckWebsites (0.00s)
        CheckWebsites_test.go:31: Wanted map[http://google.com:true http://blog.gypsydave5.com:true waat://furhurterwe.geds:false], got map[]
FAIL
exit status 1
FAIL    github.com/gypsydave5/learn-go-with-tests/concurrency/v1        0.010s

```

### Краткое отступление во вселенную параллелизма...

Возможно, вы не получите такой результат. Вы можете получить сообщение о панике, о котором мы поговорим чуть позже. Не беспокойтесь, если вы его получили, просто продолжайте запускать тест, пока *не* получите вышеуказанный результат. Или притворитесь, что получили. Решать вам. Добро пожаловать в мир параллелизма: когда он обрабатывается некорректно, трудно предсказать, что произойдет. Не беспокойтесь — именно поэтому мы пишем тесты, чтобы помочь нам узнать, когда мы обрабатываем параллелизм предсказуемо.

### ... и мы снова здесь.

Нас поймал исходный тест `CheckWebsites`, теперь он возвращает пустую карту. Что пошло не так?

Ни одна из горутин, запущенных нашим циклом `for`, не успела добавить свой результат в карту `results`; функция `CheckWebsites` слишком быстра для них, и она возвращает все еще пустую карту.

Чтобы исправить это, мы можем просто подождать, пока все горутины выполнят свою работу, а затем вернуть результат. Двух секунд должно хватить, верно?

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

Это длинно и страшно, но все, что нам нужно сделать, это перевести дух и прочитать трассировку стека: `fatal error: concurrent map writes` (фатальная ошибка: одновременная запись в карту). Иногда, когда мы запускаем наши тесты, две горутины записывают данные в карту `results` одновременно. Карты в Go не любят, когда более одного элемента пытается записать в них одновременно, и поэтому возникает `fatal error`.

Это _гонка данных_, ошибка, которая возникает, когда две или более горутины обращаются к одному и тому же участку памяти одновременно, и по крайней мере один из этих доступов является записью. Поскольку мы не можем точно контролировать, когда каждая горутина выполняется, мы уязвимы к тому, что несколько горутин пытаются записать данные в карту `results` одновременно. Карты Go не являются безопасными для одновременной записи, поэтому среда выполнения выбрасывает фатальную ошибку, чтобы предотвратить повреждение памяти.

Go может помочь нам обнаружить условия гонки (race conditions) с помощью своего встроенного [_детектора гонок данных_][godoc_race_detector]. Чтобы включить эту функцию, запустите тесты с флагом `race`: `go test -race`.

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

Детали, опять же, трудно читаемы, но `WARNING: DATA RACE` (ПРЕДУПРЕЖДЕНИЕ: ГОНКА ДАННЫХ) довольно однозначно. Вникая в тело ошибки, мы видим две разные горутины, выполняющие запись в карту:

`Write at 0x00c420084d20 by goroutine 8:` (Запись по адресу 0x00c420084d20 горутиной 8:)

записывает в тот же блок памяти, что и

`Previous write at 0x00c420084d20 by goroutine 7:` (Предыдущая запись по адресу 0x00c420084d20 горутиной 7:).

Кроме того, мы можем увидеть строку кода, где происходит запись:

`/Users/gypsydave5/go/src/github.com/gypsydave5/learn-go-with-tests/concurrency/v3/websiteChecker.go:12`

и строку кода, где горутины 7 и 8 были запущены:

`/Users/gypsydave5/go/src/github.com/gypsydave5/learn-go-with-tests/concurrency/v3/websiteChecker.go:11`

Вся необходимая информация выводится в ваш терминал — все, что вам нужно сделать, это набраться терпения, чтобы ее прочитать.

### Каналы

Мы можем решить эту гонку данных, координируя наши горутины с помощью _каналов_. Каналы — это структура данных Go, которая может как принимать, так и отправлять значения. Эти операции, наряду с их деталями, позволяют осуществлять связь между различными процессами.

В данном случае мы хотим рассмотреть связь между родительским процессом и каждой из горутин, которые он создает для выполнения работы по запуску функции `WebsiteChecker` с URL-адресом.

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

> **Заметка о `url` внутри горутины.** Каждая итерация цикла запускает новую горутину, ссылающуюся на `url`, не передавая ее явно. Начиная с Go 1.22, это безопасно: спецификация языка была изменена таким образом, что `url` является свежей переменной при каждой итерации, поэтому каждая горутина захватывает свою собственную копию.
>
> Если вы запускаете это в проекте, чей `go.mod` объявляет версию `go` *старше*, чем `1.22`, вы получите старое поведение: `url` является одной переменной, общей и повторно используемой каждой итерацией, поэтому к моменту запуска горутин они, скорее всего, увидят одно и то же (вероятно, конечное) значение `url`. Это сбивает с толку, потому что ваш Go *инструментарий* может быть новым, в то время как директива `go` вашего `go.mod` старая — инструментарий соблюдает ту семантику переменной цикла, которую подразумевает объявленная версия. Решение для старого `go.mod` состоит в явной передаче `url` в горутину: `go func(url string) { ... }(url)`.

Помимо карты `results`, у нас теперь есть `resultChannel`, который мы создаем с помощью `make` таким же образом. `chan result` — это тип канала — канал `result`. Новый тип, `result`, был создан для связывания возвращаемого значения `WebsiteChecker` с проверяемым URL-адресом — это структура из `string` и `bool`. Поскольку нам не нужно называть ни одно из этих значений, каждое из них является анонимным внутри структуры; это может быть полезно, когда трудно придумать имя для значения.

Теперь, когда мы итерируем по URL-адресам, вместо прямой записи в `map`, мы отправляем структуру `result` для каждого вызова `wc` в `resultChannel` с помощью _операции отправки_. Для этого используется оператор `<-`, который принимает канал слева и значение справа:

```go
// Операция отправки
resultChannel <- result{url, wc(url)}
```

Следующий цикл `for` итерирует один раз для каждого из URL-адресов. Внутри мы используем _операцию приёма_, которая присваивает значение, полученное из канала, переменной. Для этого также используется оператор `<-`, но с двумя операндами, теперь поменянными местами: канал находится справа, а переменная, которой мы присваиваем значение, — слева:

```go
// Операция приёма
r := <-resultChannel
```

Затем мы используем полученный `result` для обновления карты.

Отправляя результаты в канал, мы можем контролировать время каждой записи в карту результатов, гарантируя, что это происходит по очереди. Хотя каждый вызов `wc` и каждая отправка в канал результатов происходят параллельно внутри собственного процесса, каждый результат обрабатывается по одному, когда мы извлекаем значения из канала результатов с помощью операции приёма.

Мы использовали параллелизм для той части кода, которую хотели ускорить, при этом убедившись, что та часть, которая не может выполняться одновременно, все еще выполняется линейно. И мы осуществляли связь между множеством задействованных процессов, используя каналы.

Когда мы запускаем бенчмарк:

```sh
pkg: github.com/gypsydave5/learn-go-with-tests/concurrency/v2
BenchmarkCheckWebsites-8             100          23406615 ns/op
PASS
ok      github.com/gypsydave5/learn-go-with-tests/concurrency/v2        2.377s
```
23406615 наносекунд — 0.023 секунды, примерно в сто раз быстрее исходной функции. Отличный успех.

## Подведение итогов

Это упражнение было немного менее насыщенным TDD, чем обычно. В некотором смысле мы участвовали в длительном рефакторинге функции `CheckWebsites`; входы и выходы никогда не менялись, она просто стала быстрее. Но имевшиеся у нас тесты, а также написанный нами бенчмарк, позволили нам провести рефакторинг `CheckWebsites` таким образом, чтобы сохранить уверенность в работоспособности программного обеспечения, одновременно демонстрируя, что оно действительно стало быстрее.

Ускоряя ее, мы узнали о:

- *горутинах* — базовой единице параллелизма в Go, которая позволяет нам обрабатывать более одного запроса на проверку веб-сайта.
- *анонимных функциях*, которые мы использовали для запуска каждого из параллельных процессов, проверяющих веб-сайты.
- *каналах*, помогающих организовать и контролировать связь между различными процессами, что позволило нам избежать ошибки *гонки данных* (race condition).
- *детекторе гонок данных*, который помог нам отладить проблемы с параллельным кодом.

### Сделаем ее быстрой

Одна из формулировок гибкого подхода к разработке программного обеспечения, часто ошибочно приписываемая Кенту Беку, звучит так:

> [Заставьте это работать, сделайте это правильным, сделайте это быстрым][wrf]

Где «работать» означает заставить тесты проходить, «правильным» — рефакторинг кода, а «быстрым» — оптимизацию кода, чтобы он, например, работал быстро. Мы можем «сделать это быстрым» только после того, как заставили его работать и сделали его правильным. Нам повезло, что предоставленный нам код уже демонстрировал работоспособность и не требовал рефакторинга. Мы никогда не должны пытаться «сделать это быстрым» до выполнения двух других шагов, потому что

> [Преждевременная оптимизация — корень всех зол][popt]
> -- Дональд Кнут

[DI]: dependency-injection.md
[wrf]: http://wiki.c2.com/?MakeItWorkMakeItRightMakeItFast
[godoc_race_detector]: https://blog.golang.org/race-detector
[popt]: http://wiki.c2.com/?PrematureOptimization