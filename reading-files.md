# Чтение файлов

* [**Весь код для этой главы вы можете найти здесь**](https://github.com/quii/learn-go-with-tests/tree/main/reading-files)
* [Здесь вы найдете видео, где я решаю эту проблему и отвечаю на вопросы из стрима на Twitch](https://www.youtube.com/watch?v=nXts4dEJnkU)

В этой главе мы узнаем, как читать файлы, извлекать из них данные и делать что-то полезное.

Представьте, что вы работаете с другом над созданием программного обеспечения для блога. Идея состоит в том, что автор будет писать свои посты в формате markdown, с некоторыми метаданными в верхней части файла. При запуске веб-сервер будет считывать папку для создания `Post`ов, а затем отдельная функция `NewHandler` будет использовать эти `Post`ы в качестве источника данных для веб-сервера блога.

Нас попросили создать пакет, который преобразует заданную папку файлов постов блога в коллекцию `Post`ов.

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

Это требует от нас разбиения работы, но мы должны быть осторожны, чтобы не попасть в ловушку использования подхода ["снизу вверх"](https://en.wikipedia.org/wiki/Top-down_and_bottom-up_design).

Мы не должны доверять нашему чрезмерно активному воображению, когда начинаем работу. Мы могли бы поддаться искушению создать какую-то абстракцию, которая будет проверена только после того, как мы все соберем воедино, например, своего рода `BlogPostFileParser`.

Это _не_ итеративно и не позволяет использовать короткие циклы обратной связи, которые должен предоставлять TDD.

Кент Бек говорит:

> Оптимизм — это профессиональный риск программирования. Обратная связь — это лечение.

Вместо этого наш подход должен стремиться как можно быстрее обеспечить _реальную_ ценность для потребителя (часто называемый "счастливым путем"). После того как мы доставили небольшую часть потребительской ценности от начала до конца, дальнейшая итерация остальных требований обычно становится простой.

## Размышления о типе теста, который мы хотим увидеть

Давайте напомним себе о нашем мышлении и целях в начале:

* **Напишите тест, который вы хотите увидеть**. Подумайте, как мы хотели бы использовать код, который собираемся написать, с точки зрения потребителя.
* Сосредоточьтесь на _что_ и _почему_, но не отвлекайтесь на _как_.

Наш пакет должен предлагать функцию, которую можно направить на папку, и которая вернет нам посты.

```go
var posts []blogposts.Post
posts = blogposts.NewPostsFromFS("some-folder")
```

Чтобы написать тест для этого, нам понадобилась бы какая-то тестовая папка с примерами постов. _В этом нет ничего ужасного_, но вы идете на некоторые компромиссы:

* для каждого теста вам может понадобиться создавать новые файлы для проверки определенного поведения
* некоторые виды поведения будет сложно протестировать, например, неудачную загрузку файлов
* тесты будут выполняться немного медленнее, потому что им потребуется доступ к файловой системе

Мы также излишне привязываем себя к конкретной реализации файловой системы.

### Абстракции файловой системы, представленные в Go 1.16

Go 1.16 представил абстракцию для файловых систем; пакет [io/fs](https://golang.org/pkg/io/fs/).

> Пакет fs определяет базовые интерфейсы для файловой системы. Файловая система может предоставляться хостовой операционной системой, но также и другими пакетами.

Это позволяет нам ослабить привязку к конкретной файловой системе, что затем позволит нам внедрять различные реализации в соответствии с нашими потребностями.

> [Со стороны поставщика интерфейса новый тип embed.FS реализует fs.FS, как и zip.Reader. Новая функция os.DirFS предоставляет реализацию fs.FS, поддерживаемую деревом файлов операционной системы.](https://golang.org/doc/go1.16#fs)

Если мы используем этот интерфейс, пользователи нашего пакета получают ряд встроенных в стандартную библиотеку опций для использования. Изучение того, как использовать интерфейсы, определенные в стандартной библиотеке Go (например, `io.fs`, [`io.Reader`](https://golang.org/pkg/io/#Reader), [`io.Writer`](https://golang.org/pkg/io/#Writer)), жизненно важно для написания слабосвязанных пакетов. Эти пакеты затем могут быть повторно использованы в контекстах, отличных от тех, что вы предполагали, с минимальными трудностями для ваших потребителей.

В нашем случае, возможно, наш потребитель хочет, чтобы посты были встроены в бинарник Go, а не были файлами в "реальной" файловой системе? В любом случае, _нашему коду не нужно об этом беспокоиться_.

Для наших тестов пакет [testing/fstest](https://golang.org/pkg/testing/fstest/) предлагает нам реализацию [io/FS](https://golang.org/pkg/io/fs/#FS), похожую на инструменты, с которыми мы знакомы в [net/http/httptest](https://golang.org/pkg/net/http/httptest/).

Учитывая эту информацию, следующий подход кажется более удачным:

```go
var posts []blogposts.Post
posts = blogposts.NewPostsFromFS(someFS)
```

## Сначала напишите тест

Мы должны максимально сузить и сделать объем работы полезным. Если мы докажем, что можем читать все файлы в каталоге, это будет хорошим началом. Это придаст нам уверенности в разрабатываемом программном обеспечении. Мы можем проверить, что количество возвращаемых `[]Post`ов совпадает с количеством файлов в нашей фальшивой файловой системе.

Создайте новый проект для работы с этой главой.

* `mkdir blogposts`
* `cd blogposts`
* `go mod init github.com/{your-name}/blogposts`
* `touch blogposts_test.go`

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

Обратите внимание, что пакет нашего теста — `blogposts_test`. Помните, что при правильном использовании TDD мы применяем _потребительский_ подход: мы не хотим тестировать внутренние детали, потому что _потребителям_ они не интересны. Добавляя `_test` к имени нашего пакета, мы получаем доступ только к экспортируемым членам нашего пакета — точно так же, как реальный пользователь нашего пакета.

Мы импортировали [`testing/fstest`](https://golang.org/pkg/testing/fstest/), который дает нам доступ к типу [`fstest.MapFS`](https://golang.org/pkg/testing/fstest/#MapFS). Наша фальшивая файловая система будет передавать `fstest.MapFS` нашему пакету.

> `MapFS` — это простая файловая система в памяти для использования в тестах, представленная как отображение из имен путей (аргументов `Open`) к информации о файлах или каталогах, которые они представляют.

Это кажется проще, чем поддерживать папку тестовых файлов, и будет выполняться быстрее.

Наконец, мы кодифицировали использование нашего API с точки зрения потребителя, затем проверили, создает ли он правильное количество постов.

## Попробуйте запустить тест

```
./blogpost_test.go:15:12: undefined: blogposts
```

## Напишите минимальный объем кода, чтобы тест запустился, и _проверьте вывод ошибочного теста_

Пакета не существует. Создайте новый файл `blogposts.go` и поместите в него `package blogposts`. Затем вам нужно будет импортировать этот пакет в ваши тесты. У меня импорты теперь выглядят так:

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

Это вынуждает нас создать скелет нашей функции, чтобы тест запустился. Помните, не стоит переусердствовать с кодом на этом этапе; мы лишь пытаемся получить работающий тест и убедиться, что он завершается с ошибкой, как мы и ожидали. Если мы пропустим этот шаг, мы можем пропустить предположения и написать тест, который не будет полезен.

```go
package blogposts

import "testing/fstest"

type Post struct {
}

func NewPostsFromFS(fileSystem fstest.MapFS) []Post {
	return nil
}
```

Тест теперь должен правильно завершиться с ошибкой

```
=== RUN   TestNewBlogPosts
    blogposts_test.go:48: got 0 posts, wanted 2 posts
```

## Напишите достаточно кода, чтобы тест прошел

Мы _могли бы_ ["схимичить"](https://deniseyu.github.io/leveling-up-tdd/), чтобы тест прошел:

```go
func NewPostsFromFS(fileSystem fstest.MapFS) []Post {
	return []Post{{}, {}}
}
```

Но, как написала Дениз Ю:

> "Схимичить" полезно для создания "скелета" вашего объекта. Проектирование интерфейса и выполнение логики — это две разные задачи, и стратегическое использование "химичения" позволяет сосредоточиться на одной за раз.

У нас уже есть наша структура. Итак, что мы делаем вместо этого?

Поскольку мы сократили объем работ, все, что нам нужно сделать, это прочитать каталог и создать пост для каждого файла, который мы встретим. Нам пока не нужно беспокоиться об открытии и парсинге файлов.

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

[`fs.ReadDir`](https://golang.org/pkg/io/fs/#ReadDir) читает каталог внутри заданного `fs.FS`, возвращая [`[]DirEntry`](https://golang.org/pkg/io/fs/#DirEntry).

Уже наш идеализированный взгляд на мир был разрушен, потому что могут произойти ошибки, но помните, что сейчас наша цель — _заставить тест пройти_, а не менять дизайн, поэтому мы пока проигнорируем ошибку.

Остальная часть кода проста: итерируйте по записям, создайте `Post` для каждой из них и верните срез.

## Рефакторинг

Несмотря на то, что наши тесты проходят, мы не можем использовать наш новый пакет за пределами этого контекста, потому что он связан с конкретной реализацией `fstest.MapFS`. Но это не обязательно. Измените аргумент нашей функции `NewPostsFromFS`, чтобы она принимала интерфейс из стандартной библиотеки.

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

Мы отложили обработку ошибок раньше, когда сосредоточились на работе "счастливого пути". Прежде чем продолжить итерацию функциональности, мы должны признать, что при работе с файлами могут возникать ошибки. Помимо чтения каталога, мы можем столкнуться с проблемами при открытии отдельных файлов. Давайте изменим наш API (сначала через наши тесты, естественно), чтобы он мог возвращать `error`.

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

Запустите тест: он должен пожаловаться на неправильное количество возвращаемых значений. Исправить код просто.

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

Это заставит тест пройти. Практикующего TDD в вас может раздражать, что мы не видели неудачный тест, прежде чем писать код для распространения ошибки из `fs.ReadDir`. Чтобы сделать это "правильно", нам понадобился бы новый тест, где мы внедрили бы ошибочный тестовый дублер `fs.FS`, чтобы `fs.ReadDir` возвращал `error`.

```go
type StubFailingFS struct {
}

func (s StubFailingFS) Open(name string) (fs.File, error) {
	return nil, errors.New("oh no, i always fail")
}
```

```go
// later
_, err := blogposts.NewPostsFromFS(StubFailingFS{})
```

Это должно придать вам уверенности в нашем подходе. Интерфейс, который мы используем, имеет один метод, что делает создание тестовых дублеров для тестирования различных сценариев тривиальным.

В некоторых случаях тестирование обработки ошибок является прагматичным решением, но в нашем случае мы не делаем ничего _интересного_ с ошибкой, мы просто распространяем ее, поэтому нет смысла писать новый тест.

Логично, что наши следующие итерации будут связаны с расширением нашего типа `Post`, чтобы он содержал полезные данные.

## Сначала напишите тест

Мы начнем с первой строки в предложенной схеме записи блога — поля `Title`.

Нам нужно изменить содержимое тестовых файлов так, чтобы они соответствовали заданному, а затем мы сможем сделать утверждение, что оно разбирается правильно.

```go
func TestNewBlogPosts(t *testing.T) {
	fs := fstest.MapFS{
		"hello world.md":  {Data: []byte("Title: Post 1")},
		"hello-world2.md": {Data: []byte("Title: Post 2")},
	}

	// rest of test code cut for brevity
	got := posts[0]
	want := blogposts.Post{Title: "Post 1"}

	if !reflect.DeepEqual(got, want) {
		t.Errorf("got %+v, want %+v", got, want)
	}
}
```

## Попробуйте запустить тест

```
./blogpost_test.go:58:26: unknown field 'Title' in struct literal of type blogposts.Post
```

## Напишите минимальный объем кода, чтобы тест запустился, и проверьте вывод ошибочного теста

Добавьте новое поле в наш тип `Post`, чтобы тест запустился

```go
type Post struct {
	Title string
}
```

Перезапустите тест, и вы должны получить явный, ошибочный тест

```
=== RUN   TestNewBlogPosts
=== RUN   TestNewBlogPosts/parses_the_post
    blogpost_test.go:61: got {Title:}, want {Title:Post 1}
```

## Напишите достаточно кода, чтобы тест прошел

Нам нужно будет открыть каждый файл, а затем извлечь заголовок

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
			return nil, err //todo: needs clarification, should we totally fail if one file fails? or just ignore?
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

Помните, что на этом этапе наша задача — не писать элегантный код, а просто достичь момента, когда у нас будет работающее программное обеспечение.

Хотя это кажется небольшим шагом вперед, это все же потребовало от нас написания довольно большого объема кода и некоторых предположений относительно обработки ошибок. Это тот момент, когда вам следует поговорить с коллегами и решить, какой подход лучше.

Итеративный подход дал нам быструю обратную связь о том, что наше понимание требований неполно.

`fs.FS` дает нам способ открыть файл по имени с помощью его метода `Open`. Оттуда мы читаем данные из файла и, пока, нам не нужен никакой сложный парсинг, просто вырезаем текст `Title:` путем среза строки.

## Рефакторинг

Разделение кода "открытия файла" от кода "парсинга содержимого файла" сделает код более простым для понимания и работы.

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

Когда вы рефакторите новые функции или методы, будьте внимательны и подумайте об аргументах. Вы здесь занимаетесь проектированием и можете глубоко обдумывать, что уместно, потому что у вас есть проходящие тесты. Подумайте о связности и сцеплении. В этом случае вы должны спросить себя:

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

Вы можете привести аналогичный аргумент для нашей функции `getPost`, которая принимает аргумент `fs.DirEntry`, но просто вызывает `Name()` для получения имени файла. Нам все это не нужно; давайте отделимся от этого типа и передадим имя файла в виде строки. Вот полностью рефакторенный код:

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
			return nil, err //todo: needs clarification, should we totally fail if one file fails? or just ignore?
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

С этого момента большая часть наших усилий может быть аккуратно сосредоточена внутри `newPost`. Вопросы открытия и итерирования файлов решены, и теперь мы можем сосредоточиться на извлечении данных для нашего типа `Post`. Хотя это и не является технически необходимым, файлы — это хороший способ логически сгруппировать связанные вещи, поэтому я переместил тип `Post` и `newPost` в новый файл `post.go`.

### Вспомогательная функция для тестов

Мы также должны позаботиться о наших тестах. Мы будем часто делать утверждения относительно `Post`ов, поэтому нам следует написать некоторый код, чтобы помочь в этом

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

## Сначала напишите тест

Давайте расширим наш тест, чтобы извлечь следующую строку из файла — описание. До момента, когда тест начнет проходить, это должно чувствоваться комфортно и знакомо.

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

	// rest of test code cut for brevity
	assertPost(t, posts[0], blogposts.Post{
		Title:       "Post 1",
		Description: "Description 1",
	})

}
```

## Попробуйте запустить тест

```
./blogpost_test.go:47:58: unknown field 'Description' in struct literal of type blogposts.Post
```

## Напишите минимальный объем кода, чтобы тест запустился, и проверьте вывод ошибочного теста

Добавьте новое поле в `Post`.

```go
type Post struct {
	Title       string
	Description string
}
```

Тесты теперь должны скомпилироваться и завершиться с ошибкой.

```
=== RUN   TestNewBlogPosts
    blogpost_test.go:47: got {Title:Post 1
        Description: Description 1 Description:}, want {Title:Post 1 Description:Description 1}
```

## Напишите достаточно кода, чтобы тест прошел

Стандартная библиотека имеет удобную библиотеку, которая поможет вам сканировать данные построчно; [`bufio.Scanner`](https://golang.org/pkg/bufio/#Scanner)

> `Scanner` предоставляет удобный интерфейс для чтения данных, таких как файл строк текста, разделенных символом новой строки.

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

Вызовите `Scan` для чтения строки, а затем извлеките данные с помощью `Text`.

Эта функция никогда не сможет вернуть `error`. Было бы заманчиво на этом этапе удалить ее из возвращаемого типа, но мы знаем, что позже нам придется обрабатывать неверные структуры файлов, поэтому мы можем оставить ее.

## Рефакторинг

У нас повторяется сканирование строки и затем чтение текста. Мы знаем, что будем выполнять эту операцию как минимум еще раз, это простой рефакторинг для устранения дублирования, так что давайте начнем с этого.

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

Это едва ли сэкономило какие-либо строки кода, но это редко является целью рефакторинга. То, что я пытаюсь сделать здесь, это просто отделить _что_ от _как_ чтения строк, чтобы сделать код немного более декларативным для читателя.

Хотя "магические числа" 7 и 13 выполняют свою работу, они не очень описательны.

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

Теперь, когда я смотрю на код со своим творческим умом рефакторинга, я хотел бы попробовать, чтобы наша функция `readLine` сама удаляла тег. Существует также более читабельный способ обрезать префикс из строки с помощью функции `strings.TrimPrefix`.

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

Вам может понравиться или не понравиться эта идея, но мне она нравится. Суть в том, что на этапе рефакторинга мы вольны экспериментировать с внутренними деталями, и вы можете постоянно запускать тесты, чтобы убедиться, что все по-прежнему работает правильно. Мы всегда можем вернуться к предыдущим состояниям, если недовольны. Подход TDD дает нам такую возможность часто экспериментировать с идеями, чтобы у нас было больше шансов написать отличный код.

Следующее требование — извлечение тегов поста. Если вы следите за этим, я бы порекомендовал попробовать реализовать это самостоятельно, прежде чем читать дальше. Теперь у вас должен быть хороший, итеративный ритм, и вы должны чувствовать себя уверенно, чтобы извлечь следующую строку и разобрать данные.

Для краткости я не буду описывать шаги TDD, но вот тест с добавленными тегами.

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

	// rest of test code cut for brevity
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

Надеюсь, здесь нет сюрпризов. Мы смогли повторно использовать `readMetaLine`, чтобы получить следующую строку для тегов, а затем разделить их с помощью `strings.Split`.

Последняя итерация на нашем "счастливом пути" — это извлечение тела поста.

Вот напоминание о предложенном формате файла.

```markdown
Title: Hello, TDD world!
Description: First post on our wonderful blog
Tags: tdd, go
---
Hello world!

The body of posts starts after the `---`
```

Мы уже прочитали первые 3 строки. Затем нам нужно прочитать еще одну строку, отбросить ее, а затем оставшаяся часть файла будет содержать тело поста.

## Сначала напишите тест

Измените тестовые данные, чтобы они содержали разделитель и тело с несколькими новыми строками, чтобы проверить, что мы получаем весь контент.

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

Добавьте к нашему утверждению, как и к другим

```go
	assertPost(t, posts[0], blogposts.Post{
		Title:       "Post 1",
		Description: "Description 1",
		Tags:        []string{"tdd", "go"},
		Body: `Hello
World`,
	})
```

## Попробуйте запустить тест

```
./blogpost_test.go:60:3: unknown field 'Body' in struct literal of type blogposts.Post
```

Как и следовало ожидать.

## Напишите минимальный объем кода, чтобы тест запустился, и проверьте вывод ошибочного теста

Добавьте `Body` в `Post`, и тест должен завершиться с ошибкой.

```
=== RUN   TestNewBlogPosts
    blogposts_test.go:38: got {Title:Post 1 Description:Description 1 Tags:[tdd go] Body:}, want {Title:Post 1 Description:Description 1 Tags:[tdd go] Body:Hello
        World}
```

## Напишите достаточно кода, чтобы тест прошел

1. Сканировать следующую строку, чтобы проигнорировать разделитель `---`.
2. Продолжать сканирование, пока не останется данных для сканирования.

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

	scanner.Scan() // ignore a line

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

* `scanner.Scan()` возвращает `bool`, который указывает, есть ли еще данные для сканирования, поэтому мы можем использовать это с циклом `for`, чтобы продолжать читать данные до конца.
* После каждого `Scan()` мы записываем данные в буфер с помощью `fmt.Fprintln`. Мы используем версию, которая добавляет символ новой строки, потому что сканер удаляет символы новой строки из каждой строки, но нам нужно их сохранить.
* Из-за вышесказанного нам нужно обрезать конечный символ новой строки, чтобы не было лишнего.

## Рефакторинг

Инкапсуляция идеи получения оставшихся данных в функцию поможет будущим читателям быстро понять, _что_ происходит в `newPost`, не беспокоясь о деталях реализации.

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
	scanner.Scan() // ignore a line
	var b strings.Builder
	for scanner.Scan() {
		fmt.Fprintln(&b, scanner.Text())
	}
	return strings.TrimSuffix(b.String(), "\n")
}
```

## Дальнейшие итерации

Мы создали нашу "стальную нить" функциональности, пройдя кратчайший путь к нашему "счастливому пути", но, очевидно, предстоит еще долгий путь, прежде чем она будет готова к производству.

Мы не обработали:

* когда формат файла некорректен
* файл не является `.md`
* что, если порядок полей метаданных отличается? Должно ли это быть разрешено? Должны ли мы быть в состоянии это обработать?

Однако, что крайне важно, у нас есть работающее программное обеспечение, и мы определили наш интерфейс. Вышеупомянутое — это лишь дальнейшие итерации, больше тестов для написания и управления нашим поведением. Для поддержки любого из вышеперечисленного нам не придется менять наш _дизайн_, только детали реализации.

Сосредоточенность на цели означает, что мы приняли важные решения и проверили их на соответствие желаемому поведению, вместо того чтобы увязнуть в вопросах, которые не повлияют на общий дизайн.

## Подведение итогов

`fs.FS` и другие изменения в Go 1.16 предоставляют нам элегантные способы чтения данных из файловых систем и их простого тестирования.

Если вы хотите попробовать код "по-настоящему":

* Создайте папку `cmd` внутри проекта, добавьте файл `main.go`.
* Добавьте следующий код

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

* Добавьте несколько файлов markdown в папку `posts` и запустите программу!

Обратите внимание на симметрию между производственным кодом

```go
posts, err := blogposts.NewPostsFromFS(os.DirFS("posts"))
```

И тестами

```go
posts, err := blogposts.NewPostsFromFS(fs)
```

Именно тогда TDD, управляемый потребителем и построенный сверху вниз, _ощущается правильным_.

Пользователь нашего пакета может посмотреть на наши тесты и быстро понять, что он должен делать и как его использовать. Как сопровождающие, мы можем быть _уверены, что наши тесты полезны, потому что они написаны с точки зрения потребителя_. Мы не тестируем детали реализации или другие случайные детали, поэтому мы можем быть достаточно уверены, что наши тесты помогут нам, а не помешают при рефакторинге.

Опираясь на хорошие инженерные практики, такие как [**внедрение зависимостей**](dependency-injection.md), наш код становится простым для тестирования и повторного использования.

При создании пакетов, даже если они предназначены только для внутреннего использования в вашем проекте, отдавайте предпочтение подходу "сверху вниз", ориентированному на потребителя. Это убережет вас от чрезмерного воображения дизайнов и создания абстракций, которые вам могут даже не понадобиться, а также поможет убедиться, что написанные вами тесты полезны.

Итеративный подход позволял делать каждый шаг маленьким, а постоянная обратная связь помогала нам выявлять неясные требования, возможно, раньше, чем при использовании других, более нерегламентированных подходов.

### Запись?

Важно отметить, что эти новые функции имеют операции только для _чтения_ файлов. Если ваша работа требует записи, вам придется искать другие решения. Не забывайте постоянно думать о том, что в настоящее время предлагает стандартная библиотека; если вы записываете данные, вам, вероятно, следует рассмотреть возможность использования существующих интерфейсов, таких как `io.Writer`, чтобы ваш код оставался слабосвязанным и пригодным для повторного использования.

### Дополнительное чтение

* Это было легкое введение в `io/fs`. [Бен Конгдон написал отличную статью](https://benjamincongdon.me/blog/2021/01/21/A-Tour-of-Go-116s-iofs-package/), которая очень помогла при написании этой главы.
* [Обсуждение интерфейсов файловой системы](https://github.com/golang/go/issues/41190)