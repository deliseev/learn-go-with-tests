# Считыватели, осведомлённые о контексте

**[Весь код можно найти здесь](https://github.com/quii/learn-go-with-tests/tree/main/q-and-a/context-aware-reader)**

Эта глава демонстрирует, как использовать подход Test-Driven Development (TDD) для создания `io.Reader`, осведомлённого о контексте, как это было описано Мэтом Райером и Дэвидом Эрнандесом в [The Pace Dev Blog](https://pace.dev/blog/2020/02/03/context-aware-ioreader-for-golang-by-mat-ryer).

## Считыватель, осведомлённый о контексте?

Прежде всего, краткое введение в `io.Reader`.

Если вы читали другие главы этой книги, то сталкивались с `io.Reader` при открытии файлов, кодировании JSON и выполнении различных других распространенных задач. Это простая абстракция для чтения данных из _чего-либо_

```go
type Reader interface {
	Read(p []byte) (n int, err error)
}
```

Используя `io.Reader`, вы можете получить значительное повторное использование из стандартной библиотеки; это очень часто используемая абстракция (наряду с ее аналогом `io.Writer`).

### Осведомлённый о контексте?

[В предыдущей главе](context.md) мы обсуждали, как использовать `context` для обеспечения отмены. Это особенно полезно, если вы выполняете задачи, которые могут быть ресурсоемкими, и хотите иметь возможность их остановить.

Когда вы используете `io.Reader`, у вас нет гарантий по скорости: это может занять 1 наносекунду или сотни часов. Возможно, вам будет полезно иметь возможность отменять такие задачи в вашем приложении, и именно об этом писали Мэт и Дэвид.

Они объединили две простые абстракции (`context.Context` и `io.Reader`), чтобы решить эту проблему.

Давайте попробуем разработать с использованием TDD некоторую функциональность, чтобы мы могли обернуть `io.Reader` таким образом, чтобы его можно было отменить.

Тестирование этого представляет интересный вызов. Обычно при использовании `io.Reader` вы передаете его какой-либо другой функции и не особо вникаете в детали; например, `json.NewDecoder` или `io.ReadAll`.

Что мы хотим продемонстрировать, это нечто вроде:

> Дан `io.Reader` с "ABCDEF", когда я отправляю сигнал отмены на полпути, и когда я пытаюсь продолжить чтение, я больше ничего не получаю, так что всё, что я получаю, это "ABC"

Давайте снова взглянем на интерфейс.

```go
type Reader interface {
	Read(p []byte) (n int, err error)
}
```

Метод `Read` считывателя `Reader` будет считывать имеющееся содержимое в `[]byte` (срез байтов), который мы предоставляем.

Итак, вместо того чтобы читать все, мы могли бы:

 - Предоставить массив байтов фиксированного размера, который не вмещает все содержимое
 - Отправить сигнал отмены
 - Попробовать прочитать снова, и это должно вернуть ошибку с 0 прочитанными байтами

Пока что давайте просто напишем тест для "счастливого пути", где нет отмены, просто чтобы ознакомиться с проблемой, не написав еще никакого продуктового кода.

```go
func TestContextAwareReader(t *testing.T) {
	t.Run("lets just see how a normal reader works", func(t *testing.T) {
		rdr := strings.NewReader("123456")
		got := make([]byte, 3)
		_, err := rdr.Read(got)

		if err != nil {
			t.Fatal(err)
		}

		assertBufferHas(t, got, "123")

		_, err = rdr.Read(got)

		if err != nil {
			t.Fatal(err)
		}

		assertBufferHas(t, got, "456")
	})
}

func assertBufferHas(t testing.TB, buf []byte, want string) {
	t.Helper()
	got := string(buf)
	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}
```

- Создать `io.Reader` из строки с некоторыми данными
- Массив байтов (срез байтов) для чтения, который меньше содержимого считывателя
- Вызвать `read`, проверить содержимое, повторить.

Исходя из этого, мы можем представить отправку некоего сигнала отмены перед вторым чтением, чтобы изменить поведение.

Теперь, когда мы увидели, как это работает, мы будем использовать TDD для остальной функциональности.

## Сначала напишите тест

Мы хотим иметь возможность компоновать `io.Reader` с `context.Context`.

При использовании TDD лучше всего начать с представления желаемого API и написать для него тест.

Затем пусть компилятор и вывод неудавшегося теста направляют нас к решению.

```go
t.Run("behaves like a normal reader", func(t *testing.T) {
	rdr := NewCancellableReader(strings.NewReader("123456"))
	got := make([]byte, 3)
	_, err := rdr.Read(got)

	if err != nil {
		t.Fatal(err)
	}

	assertBufferHas(t, got, "123")

	_, err = rdr.Read(got)

	if err != nil {
		t.Fatal(err)
	}

	assertBufferHas(t, got, "456")
})
```

## Попробуйте запустить тест

```
./cancel_readers_test.go:12:10: undefined: NewCancellableReader
```
## Напишите минимальное количество кода, чтобы тест запустился, и проверьте вывод неудачного теста

Нам нужно будет определить эту функцию, и она должна возвращать `io.Reader`.

```go
func NewCancellableReader(rdr io.Reader) io.Reader {
	return nil
}
```

Если вы попробуете запустить его

```
=== RUN   TestCancelReaders
=== RUN   TestCancelReaders/behaves_like_a_normal_reader
panic: runtime error: invalid memory address or nil pointer dereference [recovered]
	panic: runtime error: invalid memory address or nil pointer dereference
[signal SIGSEGV: segmentation violation code=0x1 addr=0x0 pc=0x10f8fb5]
```

Как и ожидалось.

## Напишите достаточно кода, чтобы тест прошел

Пока что мы просто вернем `io.Reader`, который передали.

```go
func NewCancellableReader(rdr io.Reader) io.Reader {
	return rdr
}
```

Тест теперь должен пройти.

Я знаю, я знаю, это кажется глупым и педантичным, но прежде чем приступать к сложной работе, важно иметь _некоторую_ проверку того, что мы не нарушили "нормальное" поведение `io.Reader`, и этот тест даст нам уверенность по мере продвижения.

## Сначала напишите тест

Далее нам нужно попробовать отменить.

```go
t.Run("stops reading when cancelled", func(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	rdr := NewCancellableReader(ctx, strings.NewReader("123456"))
	got := make([]byte, 3)
	_, err := rdr.Read(got)

	if err != nil {
		t.Fatal(err)
	}

	assertBufferHas(t, got, "123")

	cancel()

	n, err := rdr.Read(got)

	if err == nil {
		t.Error("expected an error after cancellation but didn't get one")
	}

	if n > 0 {
		t.Errorf("expected 0 bytes to be read after cancellation but %d were read", n)
	}
})
```

Мы можем более или менее скопировать первый тест, но теперь мы:
- Создаем `context.Context` с отменой, чтобы мы могли `cancel` после первого чтения
- Чтобы наш код работал, нам нужно будет передать `ctx` в нашу функцию
- Затем мы утверждаем, что после `cancel` ничего не было прочитано

## Попробуйте запустить тест

```
./cancel_readers_test.go:33:30: too many arguments in call to NewCancellableReader
	have (context.Context, *strings.Reader)
	want (io.Reader)
```

## Напишите минимальное количество кода, чтобы тест запустился, и проверьте вывод неудачного теста

Компилятор говорит нам, что делать; обновить нашу сигнатуру, чтобы принимать контекст.

```go
func NewCancellableReader(ctx context.Context, rdr io.Reader) io.Reader {
	return rdr
}
```

(Вам также потребуется обновить первый тест, чтобы передавать `context.Background`).

Теперь вы должны увидеть очень ясный вывод неудачного теста.

```
=== RUN   TestCancelReaders
=== RUN   TestCancelReaders/stops_reading_when_cancelled
--- FAIL: TestCancelReaders (0.00s)
    --- FAIL: TestCancelReaders/stops_reading_when_cancelled (0.00s)
        cancel_readers_test.go:48: expected an error but didn't get one
        cancel_readers_test.go:52: expected 0 bytes to be read after cancellation but 3 were read
```

## Напишите достаточно кода, чтобы тест прошел

В этот момент это копирование из оригинальной статьи Мэта и Дэвида, но мы все равно будем двигаться медленно и итеративно.

Мы знаем, что нам нужен тип, который инкапсулирует `io.Reader`, из которого мы читаем, и `context.Context`, поэтому давайте создадим его и попробуем вернуть его из нашей функции вместо исходного `io.Reader`.

```go
func NewCancellableReader(ctx context.Context, rdr io.Reader) io.Reader {
	return &readerCtx{
		ctx:      ctx,
		delegate: rdr,
	}
}

type readerCtx struct {
	ctx      context.Context
	delegate io.Reader
}
```

Как я много раз подчеркивал в этой книге, двигайтесь медленно и позвольте компилятору помочь вам.

```
./cancel_readers_test.go:60:3: cannot use &readerCtx literal (type *readerCtx) as type io.Reader in return argument:
	*readerCtx does not implement io.Reader (missing Read method)
```

Абстракция кажется правильной, но она не реализует нужный нам интерфейс (`io.Reader`), поэтому давайте добавим метод.

```go
func (r *readerCtx) Read(p []byte) (n int, err error) {
	panic("implement me")
}
```

Запустите тесты, и они должны _скомпилироваться_, но затем вызвать панику. Это всё еще прогресс.

Давайте заставим первый тест пройти, просто _делегировав_ вызов нашему базовому `io.Reader`.

```go
func (r readerCtx) Read(p []byte) (n int, err error) {
	return r.delegate.Read(p)
}
```

На этом этапе наш тест "счастливого пути" снова проходит, и кажется, что мы хорошо абстрагировали нашу функциональность.

Чтобы наш второй тест прошел, нам нужно проверить `context.Context`, чтобы узнать, была ли произведена отмена.

```go
func (r readerCtx) Read(p []byte) (n int, err error) {
	if err := r.ctx.Err(); err != nil {
		return 0, err
	}
	return r.delegate.Read(p)
}
```

Все тесты теперь должны пройти. Вы заметите, как мы возвращаем ошибку из `context.Context`. Это позволяет вызывающим код сторонам проверять различные причины отмены, и это более подробно описано в оригинальной статье.

## Заключение

- Небольшие интерфейсы хороши и легко компонуются
- Когда вы пытаетесь дополнить что-то одно (например, `io.Reader`) другим, вы обычно хотите использовать [паттерн делегирования](https://en.wikipedia.org/wiki/Delegation_pattern)

> В программной инженерии паттерн делегирования — это объектно-ориентированный шаблон проектирования, который позволяет композиции объектов достигать той же повторной используемости кода, что и наследование.

- Простой способ начать такую работу — обернуть ваш делегат и написать тест, который утверждает, что он ведет себя так, как обычно ведет себя делегат, прежде чем вы начнете компоновать другие части для изменения поведения. Это поможет вам поддерживать корректную работу по мере продвижения к вашей цели.