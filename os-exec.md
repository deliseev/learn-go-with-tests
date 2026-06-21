# OS Exec

**[Весь код вы найдете здесь](https://github.com/quii/learn-go-with-tests/tree/main/q-and-a/os-exec)**

[keith6014](https://www.reddit.com/user/keith6014) спрашивает на [reddit](https://www.reddit.com/r/golang/comments/aaz8ji/testdata_and_function_setup_help/)

> Я выполняю команду с помощью os/exec.Command(), которая генерирует XML-данные. Команда будет выполнена в функции с именем GetData().

> Для тестирования GetData() у меня есть некоторые тестовые данные, которые я создал.

> В моем _test.go есть TestGetData, который вызывает GetData(), но он будет использовать os.exec, вместо этого я хотел бы, чтобы он использовал мои тестовые данные.

> Как этого лучше добиться? Должен ли я при вызове GetData иметь режим "test" (флаг), чтобы он читал файл, например GetData(mode string)?

Несколько моментов:

-   Если что-то трудно тестировать, это часто связано с не совсем правильным разделением ответственности (separation of concerns).
-   Не добавляйте "тестовые режимы" в свой код, вместо этого используйте [Внедрение зависимостей](./dependency-injection.md), чтобы вы могли моделировать свои зависимости и разделять ответственность.

Я взял на себя смелость предположить, как мог бы выглядеть код:

```go
type Payload struct {
	Message string `xml:"message"`
}

func GetData() string {
	cmd := exec.Command("cat", "msg.xml")

	out, _ := cmd.StdoutPipe()
	var payload Payload
	decoder := xml.NewDecoder(out)

	// these 3 can return errors but I'm ignoring for brevity
	cmd.Start()
	decoder.Decode(&payload)
	cmd.Wait()

	return strings.ToUpper(payload.Message)
}
```

-   Он использует `exec.Command`, который позволяет выполнять внешнюю команду к процессу.
-   Мы перехватываем вывод в `cmd.StdoutPipe`, который возвращает нам `io.ReadCloser` (это станет важным).
-   Остальная часть кода более или менее скопирована из [отличной документации](https://golang.org/pkg/os/exec/#example_Cmd_StdoutPipe).
    -   Мы перехватываем любой вывод из stdout в `io.ReadCloser`, затем мы `Start`'уем команду, а затем ждем, пока все данные будут прочитаны, вызвав `Wait`. Между этими двумя вызовами мы декодируем данные в нашу структуру `Payload`.

Вот что содержится в файле `msg.xml`:

```xml
<payload>
    <message>Happy New Year!</message>
</payload>
```

Я написал простой тест, чтобы показать его в действии:

```go
func TestGetData(t *testing.T) {
	got := GetData()
	want := "HAPPY NEW YEAR!"

	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}
```

## Тестируемый код

Тестируемый код является слабосвязанным и имеет одно назначение. Мне кажется, что у этого кода есть две основные задачи:

1.  Получение необработанных XML-данных
2.  Декодирование XML-данных и применение нашей бизнес-логики (в данном случае `strings.ToUpper` к `<message>`)

Первая часть — это просто копирование примера из стандартной библиотеки.

Вторая часть — это то, где находится наша бизнес-логика, и, глядя на код, мы можем увидеть, где начинается "шов" в нашей логике; это место, где мы получаем наш `io.ReadCloser`. Мы можем использовать эту существующую абстракцию для разделения ответственности и сделать наш код тестируемым.

**Проблема с GetData заключается в том, что бизнес-логика связана со способом получения XML. Чтобы улучшить наш дизайн, нам необходимо их разделить.**

Наш `TestGetData` может выступать в качестве интеграционного теста между нашими двумя задачами, поэтому мы сохраним его, чтобы убедиться, что он продолжает работать.

Вот как выглядит недавно разделенный код:

```go
type Payload struct {
	Message string `xml:"message"`
}

func GetData(data io.Reader) string {
	var payload Payload
	xml.NewDecoder(data).Decode(&payload)
	return strings.ToUpper(payload.Message)
}

func getXMLFromCommand() io.Reader {
	cmd := exec.Command("cat", "msg.xml")
	out, _ := cmd.StdoutPipe()

	cmd.Start()
	data, _ := io.ReadAll(out)
	cmd.Wait()

	return bytes.NewReader(data)
}

func TestGetDataIntegration(t *testing.T) {
	got := GetData(getXMLFromCommand())
	want := "HAPPY NEW YEAR!"

	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}
```

Теперь, когда `GetData` принимает входные данные просто из `io.Reader`, мы сделали его тестируемым, и он больше не беспокоится о том, как данные извлекаются; люди могут повторно использовать функцию с чем угодно, что возвращает `io.Reader` (что чрезвычайно распространено). Например, мы могли бы начать получать XML с URL-адреса вместо командной строки.

```go
func TestGetData(t *testing.T) {
	input := strings.NewReader(`
<payload>
    <message>Cats are the best animal</message>
</payload>`)

	got := GetData(input)
	want := "CATS ARE THE BEST ANIMAL"

	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}
```

Вот пример модульного теста для `GetData`.

Разделяя ответственность и используя существующие абстракции в Go, тестирование нашей важной бизнес-логики становится легким делом.
