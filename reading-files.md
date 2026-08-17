---
# Чтение файлов

* [**Весь код для этой главы можно найти здесь**](https://github.com/quii/learn-go-with-tests/tree/main/reading-files)
* [Здесь вы найдете видео, где я разбираю проблему и отвечаю на вопросы из стрима на Twitch](https://www.youtube.com/watch?v=nXts4dEJnkU)

В этой главе мы научимся читать файлы, извлекать из них данные и делать что-то полезное.

Представьте, что вы работаете с другом над созданием программного обеспечения для блога. Идея состоит в том, что автор будет писать свои `Post`ы в формате Markdown, с некоторыми метаданными в начале файла. При запуске веб-сервер будет считывать папку для создания `Post`ов, а затем отдельная функция `NewHandler` будет использовать эти `Post`ы в качестве источника данных для веб-сервера блога.

Нам поручено создать пакет, который преобразует заданную папку файлов с записями блога в коллекцию `Post`ов.

### Пример данных

hello world.md

```markdown
Title: Hello, TDD world!
Description: First post on our wonderful blog
Tags: tdd, go
---
Hello world!

The body of posts starts after the `---`
```

### Ожидаемые данные

```go
type Post struct {
	Title, Description, Body string
	Tags                     []string
}
```

## Итеративная разработка через тестирование

Мы будем использовать итеративный подход, постоянно предпринимая простые и безопасные шаги к нашей цели.

Это требует от нас разбиения работы, но мы должны быть осторожны, чтобы не попасть в ловушку использования ["восходящего"](https://en.wikipedia.org/wiki/Top-down_and_bottom-up_design) подхода.

Мы не должны доверять нашему чрезмерно активному воображению, когда начинаем работу. Мы могли бы поддаться искушению создать какую-то абстракцию, которая будет подтверждена только после того, как мы все соберем воедино, например, некий `BlogPostFileParser`.

Это _не_ итеративный подход, и он упускает тесные циклы обратной связи, которые должно приносить TDD.

Кент Бек говорит:

> Оптимизм — это профессиональный риск программирования. Обратная связь — это лекарство.

Вместо этого наш подход должен стремиться как можно быстрее предоставить _реальную_ ценность для потребителя (часто называемую "счастливым путем"). После того как мы предоставили небольшую часть потребительской ценности от начала до конца, дальнейшая итерация остальных требований обычно проста.

## Размышляем о том, какой тест мы хотим увидеть

Давайте напомним себе о нашем подходе и целях при старте:

*   **Напишите тест, который вы хотите увидеть**. Подумайте, как бы вы хотели использовать код, который мы собираемся написать, с точки зрения потребителя.
*   Сосредоточьтесь на _что_ и _почему_, но не отвлекайтесь на _как_.

Наш пакет должен предлагать функцию, которая может быть указана на папку и возвращать нам набор `Post`ов.

```go
var posts []blogposts.Post
posts = blogposts.NewPostsFromFS("some-folder")
```

Чтобы написать тест для этого, нам понадобится какая-то тестовая папка с несколькими примерами `Post`ов. _В этом нет ничего ужасного_, но вы идете на некоторые компромиссы:

*   для каждого теста вам может потребоваться создавать новые файлы для проверки определенного поведения
*   некоторое поведение будет сложно тестировать, например, невозможность загрузки файлов
*   тесты будут выполняться немного медленнее, так как им потребуется доступ к файловой системе

Мы также излишне привязываем себя к конкретной реализации файловой системы.

### Абстракции файловой системы, представленные в Go 1.16

Go 1.16 представил абстракцию для файловых систем; пакет [io/fs](https://golang.org/pkg/io/fs/).

> Пакет fs определяет базовые интерфейсы для файловой системы. Файловая система может быть предоставлена хостовой операционной системой, а также другими пакетами.

Это позволяет нам ослабить привязку к конкретной файловой системе, что затем позволит нам внедрять различные реализации в соответствии с нашими потребностями.

> [На стороне производителя интерфейса новый тип embed.FS реализует fs.FS, как и zip.Reader. Новая функция os.DirFS предоставляет реализацию fs.FS, основанную на дереве файлов операционной системы.](https://golang.org/doc/go1.16#fs)

Если мы используем этот интерфейс, пользователи нашего пакета имеют ряд встроенных в стандартную библиотеку опций для использования. Изучение того, как использовать интерфейсы, определенные в стандартной библиотеке Go (например, `io.fs`, [`io.Reader`](https://golang.org/pkg/io/#Reader), [`io.Writer`](https://golang.org/pkg/io/#Writer)), жизненно важно для написания слабосвязанных пакетов. Эти пакеты затем могут быть повторно использованы в контекстах, отличных от тех, что вы себе представляли, с минимальными трудностями для ваших потребителей.

В нашем случае, возможно, наш потребитель хочет, чтобы `Post`ы были встроены в бинарный файл Go, а не были файлами в "реальной" файловой системе? В любом случае, _нашему коду все равно_.

Для наших тестов пакет [testing/fstest](https://golang.org/pkg/testing/fstest/) предлагает нам реализацию [io/FS](https://golang.org/pkg/io/fs/#FS) для использования, аналогичную инструментам, с которыми мы знакомы в [net/http/httptest](https://golang.org/pkg/net/http/httptest/).

Учитывая эту информацию, следующий подход кажется лучшим:

```go
var posts []blogposts.Post
posts = blogposts.NewPostsFromFS(someFS)
```

## Сначала напишем тест

Мы должны максимально сузить и сделать область действия полезной. Если мы докажем, что можем читать все файлы в директории, это будет хорошим началом. Это придаст нам уверенности в разрабатываемом программном обеспечении. Мы можем проверить, что количество возвращаемых `[]Post`ов совпадает с количеством файлов в нашей фальшивой файловой системе.

Создайте новый проект для работы с этой главой.

*   `mkdir blogposts`
*   `cd blogposts`
*   `go mod init github.com/{your-name}/blogposts`
*   `touch blogposts_test.go`

```go
package blogposts_test

import (
	"testing"
	"testing/fstest"
)

func TestNewBlogPosts(t *testing.T) {
	fs := fstest.MapFS{
		"hello world.md":  {Data: []byte("hi")},
		"hello-world2.md": {Data: []byte("hola")},
	}

	posts := blogposts.NewPostsFromFS(fs)

	if len(posts) != len(fs) {
		t.Errorf("got %d posts, wanted %d posts", len(posts), len(fs))
	}
}
```

Обратите внимание, что пакет нашего теста — `blogposts_test`. Помните, что при правильной практике TDD мы используем _потребительский_ подход: мы не хотим тестировать внутренние детали, потому что _потребители_ о них не заботятся. Добавляя `_test` к имени нашего предполагаемого пакета, мы получаем доступ только к экспортируемым членам нашего пакета — точно так же, как реальный пользователь нашего пакета.

Мы импортировали [`testing/fstest`](https://golang.org/pkg/testing/fstest/), что дает нам доступ к типу [`fstest.MapFS`](https://golang.org/pkg/testing/fstest/#MapFS). Наша поддельная файловая система будет передавать `fstest.MapFS` нашему пакету.

> MapFS — это простая файловая система в памяти для использования в тестах, представленная как карта из имен путей (аргументы для Open) к информации о файлах или директориях, которые они представляют.

Это кажется проще, чем поддерживать папку с тестовыми файлами, и будет выполняться быстрее.

Наконец, мы кодифицировали использование нашего API с точки зрения потребителя, затем проверили, создает ли он правильное количество `Post`ов.

## Пробуем запустить тест

```
./blogpost_test.go:15:12: undefined: blogposts
```

## Пишем минимальный объем кода, чтобы тест запустился и _проверяем вывод упавшего теста_

Пакета не существует. Создайте новый файл `blogposts.go` и поместите в него `package blogposts`. Затем вам нужно будет импортировать этот пакет в свои тесты. Для меня импорты теперь выглядят так:

```go
import (
	blogposts "github.com/quii/learn-go-with-tests/reading-files"
	"testing"
	"testing/fstest"
)
```

Теперь тесты не скомпилируются, потому что наш новый пакет не имеет функции `NewPostsFromFS`, которая возвращает какую-либо коллекцию.

```
./blogpost_test.go:16:12: undefined: blogposts.NewPostsFromFS
```

Это заставляет нас создать каркас нашей функции, чтобы тест запустился. Помните, не стоит переосмысливать код на этом этапе; мы лишь пытаемся получить работающий тест и убедиться, что он падает, как мы и ожидали. Если мы пропустим этот шаг, мы можем пропустить предположения и написать бесполезный тест.

```go
package blogposts

import "testing/fstest"

type Post struct {
}

func NewPostsFromFS(fileSystem fstest.MapFS) []Post {
	return nil
}
```

Тест теперь должен правильно упасть

```
=== RUN   TestNewBlogPosts
    blogposts_test.go:48: got 0 posts, wanted 2 posts
```

## Пишем достаточно кода, чтобы тест прошел

Мы _могли бы_ ["заглушить"](https://deniseyu.github.io/leveling-up-tdd/) это, чтобы тест прошел:

```go
func NewPostsFromFS(fileSystem fstest.MapFS) []Post {
	return []Post{{}, {}}
}
```

Но, как написала Дениз Юй:

> Заглушка полезна для создания «скелета» вашего объекта. Проектирование интерфейса и выполнение логики — это две разные задачи, и стратегическое использование заглушек позволяет вам сосредоточиться на одной из них за раз.

У нас уже есть наша структура. Что же мы делаем вместо этого?

Поскольку мы сократили объем работы, все, что нам нужно сделать, это прочитать директорию и создать `Post` для каждого файла, который мы встретим. Нам пока не нужно беспокоиться об открытии файлов и их парсинге.

```go
func NewPostsFromFS(fileSystem fstest.MapFS) []Post {
	dir, _ := fs.ReadDir(fileSystem, ".")
	var posts []Post
	for range dir {
		posts = append(posts, Post{})
	}
	return posts
}
```

[`fs.ReadDir`](https://golang.org/pkg/io/fs/#ReadDir) считывает директорию внутри заданного `fs.FS`, возвращая [`[]DirEntry`](https://golang.org/pkg/io/fs/#DirEntry).

Наше идеализированное представление о мире уже было нарушено, потому что могут произойти ошибки, но помните, что сейчас наша цель — _заставить тест пройти_, а не менять дизайн, поэтому мы пока проигнорируем ошибку.

Остальная часть кода проста: итерируем записи, создаем `Post` для каждой и возвращаем срез.

## Рефакторинг

Хотя наши тесты проходят, мы не можем использовать наш новый пакет вне этого контекста, потому что он связан с конкретной реализацией `fstest.MapFS`. Но это не обязательно так. Измените аргумент нашей функции `NewPostsFromFS` так, чтобы она принимала интерфейс из стандартной библиотеки.

```go
func NewPostsFromFS(fileSystem fs.FS) []Post {
	dir, _ := fs.ReadDir(fileSystem, ".")
	var posts []Post
	for range dir {
		posts = append(posts, Post{})
	}
	return posts
}
```

Перезапустите тесты: все должно работать.

### Обработка ошибок

Мы отложили обработку ошибок на потом, когда сосредоточились на работе "счастливого пути". Прежде чем продолжать итерации по функциональности, мы должны признать, что при работе с файлами могут возникать ошибки. Помимо чтения директории, мы можем столкнуться с проблемами при открытии отдельных файлов. Давайте изменим наш API (естественно, сначала через наши тесты), чтобы он мог возвращать `error`.

```go
func TestNewBlogPosts(t *testing.T) {
	fs := fstest.MapFS{
		"hello world.md":  {Data: []byte("hi")},
		"hello-world2.md": {Data: []byte("hola")},
	}

	posts, err := blogposts.NewPostsFromFS(fs)

	if err != nil {
		t.Fatal(err)
	}

	if len(posts) != len(fs) {
		t.Errorf("got %d posts, wanted %d posts", len(posts), len(fs))
	}
}
```

Запустите тест: он должен пожаловаться на неправильное количество возвращаемых значений. Исправление кода простое.

```go
func NewPostsFromFS(fileSystem fs.FS) ([]Post, error) {
	dir, err := fs.ReadDir(fileSystem, ".")
	if err != nil {
		return nil, err
	}
	var posts []Post
	for range dir {
		posts = append(posts, Post{})
	}
	return posts, nil
}
```

Это приведет к прохождению теста. Практик TDD в вас может быть недоволен тем, что мы не увидели падающего теста перед написанием кода для распространения ошибки из `fs.ReadDir`. Чтобы сделать это "правильно", нам понадобился бы новый тест, где мы внедрим неисправный `fs.FS` test-double, чтобы `fs.ReadDir` вернул `error`.

```go
type StubFailingFS struct {
}

func (s StubFailingFS) Open(name string) (fs.File, error) {
	return nil, errors.New("oh no, i always fail")
}
```

```go
// позже
_, err := blogposts.NewPostsFromFS(StubFailingFS{})
```

Это должно дать вам уверенность в нашем подходе. Интерфейс, который мы используем, имеет один метод, что делает создание тестовых заглушек для тестирования различных сценариев тривиальным.

В некоторых случаях тестирование обработки ошибок является прагматичным решением, но в нашем случае мы не делаем с ошибкой ничего _интересного_, мы просто ее распространяем, поэтому не стоит тратить время на написание нового теста.

Логично, что наши следующие итерации будут связаны с расширением нашего типа `Post`, чтобы он содержал полезные данные.

## Сначала напишем тест

Мы начнем с первой строки в предложенной схеме `Post`а блога — поля заголовка (Title).

Нам нужно изменить содержимое тестовых файлов так, чтобы оно соответствовало заданному, а затем мы можем сделать утверждение, что оно парсится корректно.

```go
func TestNewBlogPosts(t *testing.T) {
	fs := fstest.MapFS{
		"hello world.md":  {Data: []byte("Title: Post 1")},
		"hello-world2.md": {Data: []byte("Title: Post 2")},
	}

	// остальная часть тестового кода сокращена для краткости
	got := posts[0]
	want := blogposts.Post{Title: "Post 1"}

	if !reflect.DeepEqual(got, want) {
		t.Errorf("got %+v, want %+v", got, want)
	}
}
```

## Пробуем запустить тест

```
./blogpost_test.go:58:26: unknown field 'Title' in struct literal of type blogposts.Post
```

## Пишем минимальный объем кода, чтобы тест запустился и проверяем вывод упавшего теста

Добавляем новое поле в наш тип `Post`, чтобы тест запустился:

```go
type Post struct {
	Title string
}
```

Перезапустите тест, и вы должны получить явный, падающий тест:

```
=== RUN   TestNewBlogPosts
=== RUN   TestNewBlogPosts/parses_the_post
    blogpost_test.go:61: got {Title:}, want {Title:Post 1}
```

## Пишем достаточно кода, чтобы тест прошел

Нам нужно будет открыть каждый файл, а затем извлечь заголовок (Title).

```go
func NewPostsFromFS(fileSystem fs.FS) ([]Post, error) {
	dir, err := fs.ReadDir(fileSystem, ".")
	if err != nil {
		return nil, err
	}
	var posts []Post
	for _, f := range dir {
		post, err := getPost(fileSystem, f)
		if err != nil {
			return nil, err //todo: требуется уточнение, должны ли мы полностью прекращать работу, если один файл не удалось обработать? или просто игнорировать?
		}
		posts = append(posts, post)
	}
	return posts, nil
}

func getPost(fileSystem fs.FS, f fs.DirEntry) (Post, error) {
	postFile, err := fileSystem.Open(f.Name())
	if err != nil {
		return Post{}, err
	}
	defer postFile.Close()

	postData, err := io.ReadAll(postFile)
	if err != nil {
		return Post{}, err
	}

	post := Post{Title: string(postData)[7:]}
	return post, nil
}
```

Помните, что на этом этапе наша цель не в том, чтобы написать элегантный код, а в том, чтобы получить работающее программное обеспечение.

Хотя это кажется небольшим шагом вперед, это все же потребовало от нас написания довольно большого объема кода и некоторых предположений относительно обработки ошибок. В этот момент вам следует обсудить с коллегами и решить, какой подход лучше.

Итеративный подход дал нам быструю обратную связь о том, что наше понимание требований неполно.

`fs.FS` предоставляет нам способ открытия файла по имени с помощью его метода `Open`. Оттуда мы считываем данные из файла и пока не нуждаемся в каком-либо сложном парсинге, просто вырезаем текст `Title:` путем среза строки.

## Рефакторинг

Разделение кода 'открытия файла' от кода 'парсинга содержимого файла' сделает код проще для понимания и работы.

```go
func getPost(fileSystem fs.FS, f fs.DirEntry) (Post, error) {
	postFile, err := fileSystem.Open(f.Name())
	if err != nil {
		return Post{}, err
	}
	defer postFile.Close()
	return newPost(postFile)
}

func newPost(postFile fs.File) (Post, error) {
	postData, err := io.ReadAll(postFile)
	if err != nil {
		return Post{}, err
	}

	post := Post{Title: string(postData)[7:]}
	return post, nil
}
```

Когда вы выделяете новые функции или методы, будьте внимательны и подумайте об аргументах. Вы здесь проектируете, и можете глубоко обдумать, что уместно, потому что у вас есть проходящие тесты. Подумайте о связности (coupling) и сцеплении (cohesion). В этом случае вы должны спросить себя:

> Должен ли `newPost` быть связан с `fs.File`? Используем ли мы все методы и данные из этого типа? Что нам _действительно_ нужно?

В нашем случае мы используем его только как аргумент для `io.ReadAll`, которому нужен `io.Reader`. Поэтому мы должны ослабить связность в нашей функции и запросить `io.Reader`.

```go
func newPost(postFile io.Reader) (Post, error) {
	postData, err := io.ReadAll(postFile)
	if err != nil {
		return Post{}, err
	}

	post := Post{Title: string(postData)[7:]}
	return post, nil
}
```

Аналогичный аргумент можно привести и для нашей функции `getPost`, которая принимает аргумент `fs.DirEntry`, но просто вызывает `Name()` для получения имени файла. Нам не нужно все это; давайте отделимся от этого типа и передадим имя файла в виде строки. Вот полностью рефакторенный код:

```go
func NewPostsFromFS(fileSystem fs.FS) ([]Post, error) {
	dir, err := fs.ReadDir(fileSystem, ".")
	if err != nil {
		return nil, err
	}
	var posts []Post
	for _, f := range dir {
		post, err := getPost(fileSystem, f.Name())
		if err != nil {
			return nil, err //todo: требуется уточнение, должны ли мы полностью прекращать работу, если один файл не удалось обработать? или просто игнорировать?
		}
		posts = append(posts, post)
	}
	return posts, nil
}

func getPost(fileSystem fs.FS, fileName string) (Post, error) {
	postFile, err := fileSystem.Open(fileName)
	if err != nil {
		return Post{}, err
	}
	defer postFile.Close()
	return newPost(postFile)
}

func newPost(postFile io.Reader) (Post, error) {
	postData, err := io.ReadAll(postFile)
	if err != nil {
		return Post{}, err
	}

	post := Post{Title: string(postData)[7:]}
	return post, nil
}
```

Отныне большая часть наших усилий может быть аккуратно сосредоточена внутри `newPost`. Проблемы открытия и итерации по файлам решены, и теперь мы можем сосредоточиться на извлечении данных для нашего типа `Post`. Хотя это технически не обязательно, файлы — это хороший способ логически сгруппировать связанные вещи, поэтому я переместил тип `Post` и `newPost` в новый файл `post.go`.

### Вспомогательная функция для тестов

Мы должны позаботиться и о наших тестах. Мы будем часто делать утверждения относительно `Post`ов, поэтому мы должны написать код, который поможет в этом.

```go
func assertPost(t *testing.T, got blogposts.Post, want blogposts.Post) {
	t.Helper()
	if !reflect.DeepEqual(got, want) {
		t.Errorf("got %+v, want %+v", got, want)
	}
}
```

```go
assertPost(t, posts[0], blogposts.Post{Title: "Post 1"})
```

## Сначала напишем тест

Давайте расширим наш тест, чтобы извлечь следующую строку из файла — описание (Description). Доведение его до прохождения теперь должно быть комфортным и привычным.

```go
func TestNewBlogPosts(t *testing.T) {
	const (
		firstBody = `Title: Post 1
Description: Description 1`
		secondBody = `Title: Post 2
Description: Description 2`
	)

	fs := fstest.MapFS{
		"hello world.md":  {Data: []byte(firstBody)},
		"hello-world2.md": {Data: []byte(secondBody)},
	}

	// остальная часть тестового кода сокращена для краткости
	assertPost(t, posts[0], blogposts.Post{
		Title:       "Post 1",
		Description: "Description 1",
	})

}
```

## Пробуем запустить тест

```
./blogpost_test.go:47:58: unknown field 'Description' in struct literal of type blogposts.Post
```

## Пишем минимальный объем кода, чтобы тест запустился и проверяем вывод упавшего теста

Добавляем новое поле в `Post`.

```go
type Post struct {
	Title       string
	Description string
}
```

Тесты теперь должны скомпилироваться и упасть.

```
=== RUN   TestNewBlogPosts
    blogpost_test.go:47: got {Title:Post 1
        Description: Description 1 Description:}, want {Title:Post 1 Description:Description 1}
```

## Пишем достаточно кода, чтобы тест прошел

Стандартная библиотека имеет удобную библиотеку для сканирования данных построчно; [`bufio.Scanner`](https://golang.org/pkg/bufio/#Scanner).

> Scanner предоставляет удобный интерфейс для чтения данных, таких как файл с текстовыми строками, разделенными символами новой строки.

```go
func newPost(postFile io.Reader) (Post, error) {
	scanner := bufio.NewScanner(postFile)

	scanner.Scan()
	titleLine := scanner.Text()

	scanner.Scan()
	descriptionLine := scanner.Text()

	return Post{Title: titleLine[7:], Description: descriptionLine[13:]}, nil
}
```

Удобно, что он также принимает `io.Reader` для чтения (спасибо еще раз, слабая связность), нам не нужно менять аргументы нашей функции.

Вызовите `Scan`, чтобы прочитать строку, а затем извлеките данные с помощью `Text`.

Эта функция никогда не сможет вернуть `error`. Было бы заманчиво на этом этапе удалить ее из возвращаемого типа, но мы знаем, что нам придется обрабатывать неверные структуры файлов позже, поэтому мы можем оставить ее.

## Рефакторинг

У нас есть повторение вокруг сканирования строки и затем чтения текста. Мы знаем, что будем выполнять эту операцию как минимум еще один раз, это простой рефакторинг для DRY, так что давайте начнем с этого.

```go
func newPost(postFile io.Reader) (Post, error) {
	scanner := bufio.NewScanner(postFile)

	readLine := func() string {
		scanner.Scan()
		return scanner.Text()
	}

	title := readLine()[7:]
	description := readLine()[13:]

	return Post{Title: title, Description: description}, nil
}
```

Это едва ли сэкономило какие-либо строки кода, но редко в этом заключается смысл рефакторинга. Я пытаюсь здесь просто отделить _что_ от _как_ чтения строк, чтобы сделать код немного более декларативным для читателя.

Хотя магические числа 7 и 13 справляются с задачей, они не очень описательны.

```go
const (
	titleSeparator       = "Title: "
	descriptionSeparator = "Description: "
)

func newPost(postFile io.Reader) (Post, error) {
	scanner := bufio.NewScanner(postFile)

	readLine := func() string {
		scanner.Scan()
		return scanner.Text()
	}

	title := readLine()[len(titleSeparator):]
	description := readLine()[len(descriptionSeparator):]

	return Post{Title: title, Description: description}, nil
}
```

Теперь, когда я смотрю на код со своим творческим умом для рефакторинга, я бы хотел попробовать, чтобы наша функция `readLine` сама удаляла тег. Также существует более читабельный способ обрезки префикса из строки с помощью функции `strings.TrimPrefix`.

```go
func newPost(postBody io.Reader) (Post, error) {
	scanner := bufio.NewScanner(postBody)

	readMetaLine := func(tagName string) string {
		scanner.Scan()
		return strings.TrimPrefix(scanner.Text(), tagName)
	}

	return Post{
		Title:       readMetaLine(titleSeparator),
		Description: readMetaLine(descriptionSeparator),
	}, nil
}
```

Вам может понравиться эта идея, а может и нет, но мне нравится. Суть в том, что в состоянии рефакторинга мы вольны играть с внутренними деталями, и вы можете постоянно запускать тесты, чтобы проверять, что все по-прежнему работает правильно. Мы всегда можем вернуться к предыдущим состояниям, если недовольны. Подход TDD дает нам эту свободу часто экспериментировать с идеями, поэтому у нас больше шансов написать отличный код.

Следующее требование — извлечение тегов `Post`а. Если вы следите за мной, я бы порекомендовал попробовать реализовать это самостоятельно, прежде чем читать дальше. Теперь у вас должен быть хороший, итеративный ритм, и вы должны чувствовать себя уверенно, чтобы извлекать следующую строку и парсить данные.

Для краткости я не буду проходить шаги TDD, но вот тест с добавленными тегами.

```go
func TestNewBlogPosts(t *testing.T) {
	const (
		firstBody = `Title: Post 1
Description: Description 1
Tags: tdd, go`
		secondBody = `Title: Post 2
Description: Description 2
Tags: rust, borrow-checker`
	)

	// остальная часть тестового кода сокращена для краткости
	assertPost(t, posts[0], blogposts.Post{
		Title:       "Post 1",
		Description: "Description 1",
		Tags:        []string{"tdd", "go"},
	})
}
```

Вы обманываете только себя, если просто копируете и вставляете то, что я пишу. Чтобы убедиться, что мы все на одной волне, вот мой код, который включает извлечение тегов.

```go
const (
	titleSeparator       = "Title: "
	descriptionSeparator = "Description: "
	tagsSeparator        = "Tags: "
)

func newPost(postBody io.Reader) (Post, error) {
	scanner := bufio.NewScanner(postBody)

	readMetaLine := func(tagName string) string {
		scanner.Scan()
		return strings.TrimPrefix(scanner.Text(), tagName)
	}

	return Post{
		Title:       readMetaLine(titleSeparator),
		Description: readMetaLine(descriptionSeparator),
		Tags:        strings.Split(readMetaLine(tagsSeparator), ", "),
	}, nil
}
```

Надеюсь, здесь нет никаких сюрпризов. Мы смогли повторно использовать `readMetaLine` для получения следующей строки с тегами, а затем разбить их с помощью `strings.Split`.

Последняя итерация по нашему счастливому пути — это извлечение тела `Post`а.

Вот напоминание о предложенном формате файла.

```markdown
Title: Hello, TDD world!
Description: First post on our wonderful blog
Tags: tdd, go
---
Hello world!

The body of posts starts after the `---`
```

Мы уже прочитали первые 3 строки. Затем нам нужно прочитать еще одну строку, отбросить ее, а оставшаяся часть файла будет содержать тело `Post`а.

## Сначала напишем тест

Измените тестовые данные, чтобы они содержали разделитель и тело с несколькими новыми строками, чтобы убедиться, что мы захватываем весь контент.

```go
	const (
		firstBody = `Title: Post 1
Description: Description 1
Tags: tdd, go
---
Hello
World`
		secondBody = `Title: Post 2
Description: Description 2
Tags: rust, borrow-checker
---
B
L
M`
	)
```

Добавьте к нашему утверждению, как и к остальным.

```go
	assertPost(t, posts[0], blogposts.Post{
		Title:       "Post 1",
		Description: "Description 1",
		Tags:        []string{"tdd", "go"},
		Body: `Hello
World`,
	})
```

## Пробуем запустить тест

```
./blogpost_test.go:60:3: unknown field 'Body' in struct literal of type blogposts.Post
```

Как и следовало ожидать.

## Пишем минимальный объем кода, чтобы тест запустился и проверяем вывод упавшего теста

Добавьте `Body` в `Post`, и тест должен упасть.

```
=== RUN   TestNewBlogPosts
    blogposts_test.go:38: got {Title:Post 1 Description:Description 1 Tags:[tdd go] Body:}, want {Title:Post 1 Description:Description 1 Tags:[tdd go] Body:Hello
        World}
```

## Пишем достаточно кода, чтобы тест прошел

1.  Сканировать следующую строку, чтобы игнорировать разделитель `---`.
2.  Продолжать сканирование, пока не останется данных для сканирования.

```go
func newPost(postBody io.Reader) (Post, error) {
	scanner := bufio.NewScanner(postBody)

	readMetaLine := func(tagName string) string {
		scanner.Scan()
		return strings.TrimPrefix(scanner.Text(), tagName)
	}

	title := readMetaLine(titleSeparator)
	description := readMetaLine(descriptionSeparator)
	tags := strings.Split(readMetaLine(tagsSeparator), ", ")

	scanner.Scan() // игнорируем строку

	var b strings.Builder
	for scanner.Scan() {
		fmt.Fprintln(&b, scanner.Text())
	}
	body := strings.TrimSuffix(b.String(), "\n")

	return Post{
		Title:       title,
		Description: description,
		Tags:        tags,
		Body:        body,
	}, nil
}
```

*   `scanner.Scan()` возвращает `bool`, который указывает, есть ли еще данные для сканирования, поэтому мы можем использовать это с циклом `for`, чтобы продолжать чтение данных до конца.
*   После каждого `Scan()` мы записываем данные в буфер с помощью `fmt.Fprintln`. Мы используем версию, которая добавляет новую строку, потому что сканер удаляет новые строки из каждой строки, но нам нужно их сохранить.
*   Из-за вышеизложенного нам нужно обрезать конечную новую строку, чтобы не было лишней.

## Рефакторинг

Инкапсуляция идеи получения оставшихся данных в функцию поможет будущим читателям быстро понять, _что_ происходит в `newPost`, не заботясь о деталях реализации.

```go
func newPost(postBody io.Reader) (Post, error) {
	scanner := bufio.NewScanner(postBody)

	readMetaLine := func(tagName string) string {
		scanner.Scan()
		return strings.TrimPrefix(scanner.Text(), tagName)
	}

	return Post{
		Title:       readMetaLine(titleSeparator),
		Description: readMetaLine(descriptionSeparator),
		Tags:        strings.Split(readMetaLine(tagsSeparator), ", "),
		Body:        readBody(scanner),
	}, nil
}

func readBody(scanner *bufio.Scanner) string {
	scanner.Scan() // игнорируем строку
	var b strings.Builder
	for scanner.Scan() {
		fmt.Fprintln(&b, scanner.Text())
	}
	return strings.TrimSuffix(b.String(), "\n")
}
```

## Дальнейшие итерации

Мы создали нашу "стальную нить" функциональности, пройдя кратчайший путь к нашему "счастливому пути", но очевидно, что предстоит пройти еще некоторое расстояние, прежде чем она будет готова к продакшену.

Мы не обработали:

*   когда формат файла неверен
*   файл не является `.md`
*   что, если порядок полей метаданных отличается? Должно ли это быть разрешено? Должны ли мы быть в состоянии это обработать?

Однако, что крайне важно, у нас есть работающее программное обеспечение, и мы определили наш интерфейс. Вышеупомянутое — это лишь дальнейшие итерации, больше тестов для написания и управления нашим поведением. Чтобы поддержать любое из вышеперечисленного, нам не придется менять наш _дизайн_, только детали реализации.

Сохранение фокуса на цели означает, что мы приняли важные решения и проверили их на соответствие желаемому поведению, вместо того чтобы увязнуть в вопросах, которые не повлияют на общий дизайн.

## Подводим итоги

`fs.FS` и другие изменения в Go 1.16 предоставляют нам элегантные способы чтения данных из файловых систем и их простого тестирования.

Если вы хотите опробовать код "по-настоящему":

*   Создайте папку `cmd` в проекте, добавьте файл `main.go`.
*   Добавьте следующий код:

```go
import (
	blogposts "github.com/quii/fstest-spike"
	"log"
	"os"
)

func main() {
	posts, err := blogposts.NewPostsFromFS(os.DirFS("posts"))
	if err != nil {
		log.Fatal(err)
	}
	log.Println(posts)
}
```

*   Добавьте несколько Markdown-файлов в папку `posts` и запустите программу!

Обратите внимание на симметрию между производственным кодом:

```go
posts, err := blogposts.NewPostsFromFS(os.DirFS("posts"))
```

И тестами:

```go
posts, err := blogposts.NewPostsFromFS(fs)
```

Именно тогда TDD, управляемый потребителем и использующий нисходящий подход, _чувствуется правильным_.

Пользователь нашего пакета может посмотреть на наши тесты и быстро понять, что он должен делать и как его использовать. Как сопровождающие, мы можем быть _уверены, что наши тесты полезны, потому что они написаны с точки зрения потребителя_. Мы не тестируем детали реализации или другие случайные детали, поэтому мы можем быть достаточно уверены, что наши тесты помогут нам, а не помешают при рефакторинге.

Полагаясь на хорошие методы разработки программного обеспечения, такие как [**внедрение зависимостей**](dependency-injection.md), наш код прост для тестирования и повторного использования.

При создании пакетов, даже если они предназначены только для вашего проекта, предпочитайте нисходящий подход, управляемый потребителем. Это предотвратит чрезмерное воображение дизайнов и создание абстракций, которые вам могут даже не понадобиться, и поможет гарантировать, что написанные вами тесты будут полезными.

Итеративный подход позволил делать каждый шаг небольшим, а непрерывная обратная связь помогла нам выявить неясные требования, возможно, раньше, чем при других, более несистематических подходах.

### Запись?

Важно отметить, что эти новые функции имеют операции только для _чтения_ файлов. Если ваша работа требует записи, вам нужно будет искать другие средства. Помните, что следует постоянно думать о том, что предлагает стандартная библиотека; если вы пишете данные, вам, вероятно, стоит рассмотреть возможность использования существующих интерфейсов, таких как `io.Writer`, чтобы ваш код оставался слабосвязанным и пригодным для повторного использования.

### Дополнительное чтение

*   Это было краткое введение в `io/fs`. [Бен Конгдон написал отличную статью](https://benjamincongdon.me/blog/2021/01/21/A-Tour-of-Go-116s-iofs-package/), которая очень помогла при написании этой главы.
*   [Обсуждение интерфейсов файловой системы](https://github.com/golang/go/issues/41190)
---