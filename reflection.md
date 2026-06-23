# Рефлексия

**[Весь код для этой главы вы найдете здесь](https://github.com/quii/learn-go-with-tests/tree/main/reflection)**

[Из Твиттера](https://twitter.com/peterbourgon/status/1011403901419937792?s=09)

> golang challenge: напишите функцию `walk(x interface{}, fn func(string))`, которая принимает структуру `x` и вызывает `fn` для всех строковых полей, найденных внутри. уровень сложности: рекурсивно.

Для этого нам понадобится использовать _рефлексию_.

> Рефлексия в программировании — это способность программы исследовать свою собственную структуру, в частности, через типы; это форма метапрограммирования. Это также является большим источником путаницы.

Из [The Go Blog: Reflection](https://blog.golang.org/laws-of-reflection)

## Что такое `interface{}`?

Мы наслаждались типовой безопасностью, которую Go предлагает нам в функциях, работающих с известными типами, такими как `string`, `int` и нашими собственными типами, такими как `BankAccount`.

Это означает, что мы получаем некоторую документацию бесплатно, и компилятор будет жаловаться, если вы попытаетесь передать функции неверный тип.

Однако вы можете столкнуться со сценариями, когда вы хотите написать функцию, в которой тип неизвестен во время компиляции.

Go позволяет нам обойти это с помощью типа `interface{}`, который можно рассматривать как _любой_ тип (на самом деле, в Go `any` является [псевдонимом](https://cs.opensource.google/go/go/+/master:src/builtin/builtin.go;drc=master;l=95) для `interface{}`).

Таким образом, `walk(x interface{}, fn func(string))` будет принимать любое значение для `x`.

### Так почему бы не использовать `interface{}` для всего и не иметь действительно гибких функций?

- Как пользователь функции, которая принимает `interface{}`, вы теряете типовую безопасность. Что, если вы хотели передать `Herd.species` типа `string` в функцию, но вместо этого передали `Herd.count`, которое является `int`? Компилятор не сможет сообщить вам о вашей ошибке. Вы также понятия не имеете, _что_ вам разрешено передавать функции. Знание того, что функция принимает, например, `UserService`, очень полезно.
- Как автор такой функции, вы должны иметь возможность проверять _все_, что вам было передано, и пытаться выяснить, что это за тип и что вы можете с ним делать. Это делается с помощью _рефлексии_. Это может быть довольно громоздко и трудночитаемо, и, как правило, менее производительно (поскольку вам приходится выполнять проверки во время выполнения).

Короче говоря, используйте рефлексию только в том случае, если вам это действительно необходимо.

Если вы хотите использовать полиморфные функции, подумайте, можете ли вы спроектировать их на основе интерфейса (не `interface{}`, что сбивает с толку), чтобы пользователи могли использовать вашу функцию с несколькими типами, если они реализуют любые методы, необходимые для работы вашей функции.

Наша функция должна будет работать с множеством различных вещей. Как всегда, мы будем использовать итеративный подход, писать тесты для каждой новой вещи, которую мы хотим поддерживать, и рефакторить по ходу дела, пока не закончим.

## Сначала напишем тест

Мы захотим вызвать нашу функцию со структурой, содержащей строковое поле (`x`). Затем мы сможем "шпионить" за переданной функцией (`fn`), чтобы проверить, была ли она вызвана.

```go
func TestWalk(t *testing.T) {

	expected := "Chris"
	var got []string

	x := struct {
		Name string
	}{expected}

	walk(x, func(input string) {
		got = append(got, input)
	})

	if len(got) != 1 {
		t.Errorf("wrong number of function calls, got %d want %d", len(got), 1)
	}
}
```

- Мы хотим сохранить срез строк (`got`), который хранит строки, переданные в `fn` функцией `walk`. Часто в предыдущих главах мы создавали для этого выделенные типы, чтобы "шпионить" за вызовами функций/методов, но в данном случае мы можем просто передать анонимную функцию для `fn`, которая захватывает `got`.
- Мы используем анонимную `структуру` с полем `Name` строкового типа для простейшего "счастливого" пути.
- Наконец, вызываем `walk` с `x` и "шпионом", и пока просто проверяем длину `got`; мы будем более конкретны в наших утверждениях, как только у нас заработает что-то очень простое.

## Попробуем запустить тест

```
./reflection_test.go:21:2: undefined: walk
```

## Напишем минимальный код для запуска теста и проверим вывод неудачного теста

Нам нужно определить `walk`

```go
func walk(x interface{}, fn func(input string)) {

}
```

Попробуем запустить тест снова

```
=== RUN   TestWalk
--- FAIL: TestWalk (0.00s)
    reflection_test.go:19: wrong number of function calls, got 0 want 1
FAIL
```

## Напишем достаточно кода, чтобы тест прошел

Мы можем вызвать "шпиона" с любой строкой, чтобы тест прошел.

```go
func walk(x interface{}, fn func(input string)) {
	fn("I still can't believe South Korea beat Germany 2-0 to put them last in their group")
}
```

Тест теперь должен проходить. Следующее, что нам нужно будет сделать, это более конкретное утверждение о том, с чем вызывается наша `fn`.

## Сначала напишем тест

Добавьте следующее в существующий тест, чтобы проверить, что строка, переданная `fn`, верна

```go
if got[0] != expected {
	t.Errorf("got %q, want %q", got[0], expected)
}
```

## Попробуем запустить тест

```
=== RUN   TestWalk
--- FAIL: TestWalk (0.00s)
    reflection_test.go:23: got 'I still can't believe South Korea beat Germany 2-0 to put them last in their group', want 'Chris'
FAIL
```

## Напишем достаточно кода, чтобы тест прошел

```go
func walk(x interface{}, fn func(input string)) {
	val := reflect.ValueOf(x)
	field := val.Field(0)
	fn(field.String())
}
```

Этот код _очень небезопасен и очень наивен_, но помните: наша цель, когда мы находимся в "красной" зоне (тесты не проходят), — написать минимально возможное количество кода. Затем мы пишем больше тестов, чтобы решить наши проблемы.

Нам нужно использовать рефлексию, чтобы взглянуть на `x` и попытаться изучить его свойства.

Пакет [reflect](https://pkg.go.dev/reflect) содержит функцию `ValueOf`, которая возвращает нам `Value` заданной переменной. Это позволяет нам исследовать значение, включая его поля, которые мы используем в следующей строке.

Затем мы делаем несколько очень оптимистичных предположений о переданном значении:

- Мы смотрим на первое и единственное поле. Однако полей может не быть вовсе, что вызовет панику.
- Затем мы вызываем `String()`, которая возвращает базовое значение в виде строки. Однако это было бы неверно, если бы поле было чем-то иным, чем строка.

## Рефакторинг

Наш код проходит для простого случая, но мы знаем, что у нашего кода есть много недостатков.

Мы собираемся написать ряд тестов, в которых будем передавать различные значения и проверять срез строк, с которым была вызвана `fn`.

Нам следует рефакторить наш тест в табличный тест, чтобы упростить дальнейшее тестирование новых сценариев.

```go
func TestWalk(t *testing.T) {

	cases := []struct {
		Name          string
		Input         interface{}
		ExpectedCalls []string
	}{
		{
			"struct with one string field",
			struct {
				Name string
			}{"Chris"},
			[]string{"Chris"},
		},
	}

	for _, test := range cases {
		t.Run(test.Name, func(t *testing.T) {
			var got []string
			walk(test.Input, func(input string) {
				got = append(got, input)
			})

			if !reflect.DeepEqual(got, test.ExpectedCalls) {
				t.Errorf("got %v, want %v", got, test.ExpectedCalls)
			}
		})
	}
}
```

Теперь мы можем легко добавить сценарий, чтобы увидеть, что произойдет, если у нас будет более одного строкового поля.

## Сначала напишем тест

Добавьте следующий сценарий в `cases`.

```
{
    "struct with two string fields",
    struct {
        Name string
        City string
    }{"Chris", "London"},
    []string{"Chris", "London"},
},
```

## Попробуем запустить тест

```
=== RUN   TestWalk/struct_with_two_string_fields
    --- FAIL: TestWalk/struct_with_two_string_fields (0.00s)
        reflection_test.go:40: got [Chris], want [Chris London]
```

## Напишем достаточно кода, чтобы тест прошел

```go
func walk(x interface{}, fn func(input string)) {
	val := reflect.ValueOf(x)

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)
		fn(field.String())
	}
}
```

`val` имеет метод `NumField`, который возвращает количество полей в значении. Это позволяет нам итерировать поля и вызывать `fn`, что приводит к прохождению нашего теста.

## Рефакторинг

Похоже, здесь нет очевидных рефакторингов, которые улучшили бы код, так что давайте продолжим.

Следующий недостаток `walk` заключается в том, что она предполагает, что каждое поле является `string`. Давайте напишем тест для этого сценария.

## Сначала напишем тест

Добавьте следующий случай

```
{
    "struct with non string field",
    struct {
        Name string
        Age  int
    }{"Chris", 33},
    []string{"Chris"},
},
```

## Попробуем запустить тест

```
=== RUN   TestWalk/struct_with_non_string_field
    --- FAIL: TestWalk/struct_with_non_string_field (0.00s)
        reflection_test.go:46: got [Chris <int Value>], want [Chris]
```

## Напишем достаточно кода, чтобы тест прошел

Нам нужно проверить, что тип поля — `string`.

```go
func walk(x interface{}, fn func(input string)) {
	val := reflect.ValueOf(x)

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)

		if field.Kind() == reflect.String {
			fn(field.String())
		}
	}
}
```

Мы можем это сделать, проверив его [`Kind`](https://pkg.go.dev/reflect#Kind).

## Рефакторинг

И снова, похоже, что код достаточно разумный на данный момент.

Следующий сценарий: что, если это не "плоская" `структура`? Другими словами, что произойдет, если у нас есть `структура` с некоторыми вложенными полями?

## Сначала напишем тест

Мы использовали синтаксис анонимных структур для ситуативного объявления типов в наших тестах, поэтому могли бы продолжить делать это так:

```
{
    "nested fields",
    struct {
        Name string
        Profile struct {
            Age  int
            City string
        }
    }{"Chris", struct {
        Age  int
        City string
    }{33, "London"}},
    []string{"Chris", "London"},
},
```

Но мы видим, что когда появляются вложенные анонимные структуры, синтаксис становится немного громоздким. [Есть предложение сделать синтаксис более приятным](https://github.com/golang/go/issues/12854).

Давайте просто рефакторим это, создав известный тип для этого сценария и сославшись на него в тесте. Здесь есть небольшая косвенность в том, что часть кода для нашего теста находится вне теста, но читатели должны быть в состоянии вывести структуру `структуры`, глядя на инициализацию.

Добавьте следующие объявления типов где-нибудь в ваш тестовый файл

```go
type Person struct {
	Name    string
	Profile Profile
}

type Profile struct {
	Age  int
	City string
}
```

Теперь мы можем добавить это в наши тестовые случаи, что читается намного понятнее, чем раньше

```
{
    "nested fields",
    Person{
        "Chris",
        Profile{33, "London"},
    },
    []string{"Chris", "London"},
},
```

## Попробуем запустить тест

```
=== RUN   TestWalk/Nested_fields
    --- FAIL: TestWalk/nested_fields (0.00s)
        reflection_test.go:54: got [Chris], want [Chris London]
```

Проблема в том, что мы итерируем только поля на первом уровне иерархии типа.

## Напишем достаточно кода, чтобы тест прошел

Решение довольно простое: мы снова проверяем его `Kind`, и если это оказывается `структура`, мы просто снова вызываем `walk` для этой внутренней `структуры`.

```go
func walk(x interface{}, fn func(input string)) {
	val := reflect.ValueOf(x)

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)

		if field.Kind() == reflect.String {
			fn(field.String())
		}

		if field.Kind() == reflect.Struct {
			walk(field.Interface(), fn)
		}
	}
}
```

## Рефакторинг

Когда вы сравниваете одно и то же значение более одного раза, _обычно_ рефакторинг с использованием `switch` улучшит читаемость и сделает ваш код более легким для расширения.

```go
func walk(x interface{}, fn func(input string)) {
	val := reflect.ValueOf(x)

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)

		switch field.Kind() {
		case reflect.String:
			fn(field.String())
		case reflect.Struct:
			walk(field.Interface(), fn)
		}
	}
}
```

Что, если значение переданной структуры является указателем?

## Сначала напишем тест

Добавьте этот случай

```
{
    "pointers to things",
    &Person{
        "Chris",
        Profile{33, "London"},
    },
    []string{"Chris", "London"},
},
```

## Попробуем запустить тест

```
=== RUN   TestWalk/pointers_to_things
panic: reflect: call of reflect.Value.NumField on ptr Value [recovered]
    panic: reflect: call of reflect.Value.NumField on ptr Value
```

## Напишем достаточно кода, чтобы тест прошел

Вы не можете использовать `NumField` на `Value` указателя, нам нужно извлечь базовое значение, прежде чем мы сможем это сделать, используя `Elem()`.

```go
func walk(x interface{}, fn func(input string)) {
	val := reflect.ValueOf(x)

	if val.Kind() == reflect.Pointer {
		val = val.Elem()
	}

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)

		switch field.Kind() {
		case reflect.String:
			fn(field.String())
		case reflect.Struct:
			walk(field.Interface(), fn)
		}
	}
}
```

## Рефакторинг

Давайте инкапсулируем ответственность за извлечение `reflect.Value` из данного `interface{}` в отдельную функцию.

```go
func walk(x interface{}, fn func(input string)) {
	val := getValue(x)

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)

		switch field.Kind() {
		case reflect.String:
			fn(field.String())
		case reflect.Struct:
			walk(field.Interface(), fn)
		}
	}
}

func getValue(x interface{}) reflect.Value {
	val := reflect.ValueOf(x)

	if val.Kind() == reflect.Pointer {
		val = val.Elem()
	}

	return val
}
```

Это на самом деле добавляет _больше_ кода, но я чувствую, что уровень абстракции правильный.

- Получить `reflect.Value` от `x`, чтобы я мог его исследовать, мне все равно, как.
- Итерировать по полям, выполняя то, что необходимо, в зависимости от их типа.

Далее, нам нужно рассмотреть срезы.

## Сначала напишем тест

```
{
    "slices",
    []Profile {
        {33, "London"},
        {34, "Reykjavík"},
    },
    []string{"London", "Reykjavík"},
},
```

## Попробуем запустить тест

```
=== RUN   TestWalk/slices
panic: reflect: call of reflect.Value.NumField on slice Value [recovered]
    panic: reflect: call of reflect.Value.NumField on slice Value
```

## Напишем минимальный код для запуска теста и проверим вывод неудачного теста

Это похоже на предыдущий сценарий с указателем: мы пытаемся вызвать `NumField` на нашем `reflect.Value`, но у него его нет, так как это не структура.

## Напишем достаточно кода, чтобы тест прошел

```go
func walk(x interface{}, fn func(input string)) {
	val := getValue(x)

	if val.Kind() == reflect.Slice {
		for i := 0; i < val.Len(); i++ {
			walk(val.Index(i).Interface(), fn)
		}
		return
	}

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)

		switch field.Kind() {
		case reflect.String:
			fn(field.String())
		case reflect.Struct:
			walk(field.Interface(), fn)
		}
	}
}
```

## Рефакторинг

Это работает, но это неприятно. Не беспокойтесь, у нас есть рабочий код, подкрепленный тестами, так что мы можем изменять его сколько угодно.

Если подумать немного абстрактно, мы хотим вызвать `walk` либо:

- Для каждого поля в структуре
- Для каждой _вещи_ в срезе

Наш код на данный момент делает это, но не отражает это очень хорошо. У нас просто есть проверка в начале, чтобы увидеть, является ли это срезом (с `return`, чтобы остановить выполнение остального кода), и если нет, мы просто предполагаем, что это структура.

Давайте переработаем код так, чтобы сначала мы проверяли тип, а затем выполняли нашу работу.

```go
func walk(x interface{}, fn func(input string)) {
	val := getValue(x)

	switch val.Kind() {
	case reflect.Struct:
		for i := 0; i < val.NumField(); i++ {
			walk(val.Field(i).Interface(), fn)
		}
	case reflect.Slice:
		for i := 0; i < val.Len(); i++ {
			walk(val.Index(i).Interface(), fn)
		}
	case reflect.String:
		fn(val.String())
	}
}
```

Выглядит гораздо лучше! Если это структура или срез, мы итерируем по ее значениям, вызывая `walk` для каждого из них. В противном случае, если это `reflect.String`, мы можем вызвать `fn`.

Тем не менее, мне кажется, что можно сделать лучше. Повторяется операция итерации по полям/значениям с последующим вызовом `walk`, но концептуально они одинаковы.

```go
func walk(x interface{}, fn func(input string)) {
	val := getValue(x)

	numberOfValues := 0
	var getField func(int) reflect.Value

	switch val.Kind() {
	case reflect.String:
		fn(val.String())
	case reflect.Struct:
		numberOfValues = val.NumField()
		getField = val.Field
	case reflect.Slice:
		numberOfValues = val.Len()
		getField = val.Index
	}

	for i := 0; i < numberOfValues; i++ {
		walk(getField(i).Interface(), fn)
	}
}
```

Если `value` является `reflect.String`, то мы просто вызываем `fn` как обычно.

В противном случае наш `switch` извлечет две вещи в зависимости от типа:

- Сколько полей существует
- Как извлечь `Value` (`Field` или `Index`)

Как только мы определили эти вещи, мы можем итерировать `numberOfValues`, вызывая `walk` с результатом функции `getField`.

Теперь, когда мы это сделали, обработка массивов должна быть тривиальной.

## Сначала напишем тест

Добавьте в тестовые случаи

```
{
    "arrays",
    [2]Profile {
        {33, "London"},
        {34, "Reykjavík"},
    },
    []string{"London", "Reykjavík"},
},
```

## Попробуем запустить тест

```
=== RUN   TestWalk/arrays
    --- FAIL: TestWalk/arrays (0.00s)
        reflection_test.go:78: got [], want [London Reykjavík]
```

## Напишем достаточно кода, чтобы тест прошел

Массивы можно обрабатывать так же, как и срезы, поэтому просто добавьте их в case через запятую.

```go
func walk(x interface{}, fn func(input string)) {
	val := getValue(x)

	numberOfValues := 0
	var getField func(int) reflect.Value

	switch val.Kind() {
	case reflect.String:
		fn(val.String())
	case reflect.Struct:
		numberOfValues = val.NumField()
		getField = val.Field
	case reflect.Slice, reflect.Array:
		numberOfValues = val.Len()
		getField = val.Index
	}

	for i := 0; i < numberOfValues; i++ {
		walk(getField(i).Interface(), fn)
	}
}
```

Следующий тип, который мы хотим обрабатывать, — `map`.

## Сначала напишем тест

```
{
    "maps",
    map[string]string{
        "Cow": "Moo",
        "Sheep": "Baa",
    },
    []string{"Moo", "Baa"},
},
```

## Попробуем запустить тест

```
=== RUN   TestWalk/maps
    --- FAIL: TestWalk/maps (0.00s)
        reflection_test.go:86: got [], want [Moo Baa]
```

## Напишем достаточно кода, чтобы тест прошел

И снова, если подумать немного абстрактно, можно увидеть, что `map` очень похож на `структуру`, просто ключи неизвестны во время компиляции.

```go
func walk(x interface{}, fn func(input string)) {
	val := getValue(x)

	numberOfValues := 0
	var getField func(int) reflect.Value

	switch val.Kind() {
	case reflect.String:
		fn(val.String())
	case reflect.Struct:
		numberOfValues = val.NumField()
		getField = val.Field
	case reflect.Slice, reflect.Array:
		numberOfValues = val.Len()
		getField = val.Index
	case reflect.Map:
		for _, key := range val.MapKeys() {
			walk(val.MapIndex(key).Interface(), fn)
		}
	}

	for i := 0; i < numberOfValues; i++ {
		walk(getField(i).Interface(), fn)
	}
}
```

Однако по замыслу вы не можете получить значения из карты по индексу. Это делается только по _ключу_, что нарушает нашу абстракцию, черт возьми.

## Рефакторинг

Как вы себя сейчас чувствуете? Тогда казалось, что это, возможно, хорошая абстракция, но теперь код кажется немного шатким.

_Это нормально!_ Рефакторинг — это путешествие, и иногда мы будем совершать ошибки. Важный момент TDD заключается в том, что он дает нам свободу пробовать эти вещи.

Делая маленькие шаги, подкрепленные тестами, эта ситуация ни в коем случае не является необратимой. Давайте просто вернем ее к тому, как это было до рефакторинга.

```go
func walk(x interface{}, fn func(input string)) {
	val := getValue(x)

	walkValue := func(value reflect.Value) {
		walk(value.Interface(), fn)
	}

	switch val.Kind() {
	case reflect.String:
		fn(val.String())
	case reflect.Struct:
		for i := 0; i < val.NumField(); i++ {
			walkValue(val.Field(i))
		}
	case reflect.Slice, reflect.Array:
		for i := 0; i < val.Len(); i++ {
			walkValue(val.Index(i))
		}
	case reflect.Map:
		for _, key := range val.MapKeys() {
			walkValue(val.MapIndex(key))
		}
	}
}
```

Мы ввели `walkValue`, которая устраняет дублирование вызовов `walk` внутри нашего `switch`, так что им нужно только извлекать `reflect.Value` из `val`.

### Одна последняя проблема

Помните, что `map` в Go не гарантируют порядок. Поэтому ваши тесты иногда будут завершаться неудачей, потому что мы утверждаем, что вызовы `fn` выполняются в определенном порядке.

Чтобы исправить это, нам нужно будет перенести наше утверждение с `map` в новый тест, где порядок нам не важен.

```go
t.Run("with maps", func(t *testing.T) {
	aMap := map[string]string{
		"Cow":   "Moo",
		"Sheep": "Baa",
	}

	var got []string
	walk(aMap, func(input string) {
		got = append(got, input)
	})

	assertContains(t, got, "Moo")
	assertContains(t, got, "Baa")
})
```

Вот как определена `assertContains`

```go
func assertContains(t testing.TB, haystack []string, needle string) {
	t.Helper()
	contains := false
	for _, x := range haystack {
		if x == needle {
			contains = true
		}
	}
	if !contains {
		t.Errorf("expected %v to contain %q but it didn't", haystack, needle)
	}
}
```

Поскольку мы вынесли `map` в отдельный тест, мы не видели сообщение об ошибке. Намеренно сломайте здесь тест `with maps`, чтобы вы могли проверить сообщение об ошибке, а затем снова исправьте его, чтобы все тесты проходили.

Следующий тип, который мы хотим обрабатывать, — `chan`.

## Сначала напишем тест

```go
t.Run("with channels", func(t *testing.T) {
	aChannel := make(chan Profile)

	go func() {
		aChannel <- Profile{33, "Berlin"}
		aChannel <- Profile{34, "Katowice"}
		close(aChannel)
	}()

	var got []string
	want := []string{"Berlin", "Katowice"}

	walk(aChannel, func(input string) {
		got = append(got, input)
	})

	if !reflect.DeepEqual(got, want) {
		t.Errorf("got %v, want %v", got, want)
	}
})
```

## Попробуем запустить тест

```
--- FAIL: TestWalk (0.00s)
    --- FAIL: TestWalk/with_channels (0.00s)
        reflection_test.go:115: got [], want [Berlin Katowice]
```

## Напишем достаточно кода, чтобы тест прошел

Мы можем итерировать по всем значениям, отправленным через канал, пока он не будет закрыт с помощью Recv()

```go
func walk(x interface{}, fn func(input string)) {
	val := getValue(x)

	walkValue := func(value reflect.Value) {
		walk(value.Interface(), fn)
	}

	switch val.Kind() {
	case reflect.String:
		fn(val.String())
	case reflect.Struct:
		for i := 0; i < val.NumField(); i++ {
			walkValue(val.Field(i))
		}
	case reflect.Slice, reflect.Array:
		for i := 0; i < val.Len(); i++ {
			walkValue(val.Index(i))
		}
	case reflect.Map:
		for _, key := range val.MapKeys() {
			walkValue(val.MapIndex(key))
		}
	case reflect.Chan:
		for {
			if v, ok := val.Recv(); ok {
				walkValue(v)
			} else {
				break
			}
		}
	}
}
```

Следующий тип, который мы хотим обрабатывать, — `func`.

## Сначала напишем тест

```go
t.Run("with function", func(t *testing.T) {
	aFunction := func() (Profile, Profile) {
		return Profile{33, "Berlin"}, Profile{34, "Katowice"}
	}

	var got []string
	want := []string{"Berlin", "Katowice"}

	walk(aFunction, func(input string) {
		got = append(got, input)
	})

	if !reflect.DeepEqual(got, want) {
		t.Errorf("got %v, want %v", got, want)
	}
})
```

## Попробуем запустить тест

```
--- FAIL: TestWalk (0.00s)
    --- FAIL: TestWalk/with_function (0.00s)
        reflection_test.go:132: got [], want [Berlin Katowice]
```

## Напишем достаточно кода, чтобы тест прошел

Функции без аргументов не имеют особого смысла в этом сценарии. Но мы должны предусмотреть возможность произвольных возвращаемых значений.

```go
func walk(x interface{}, fn func(input string)) {
	val := getValue(x)

	walkValue := func(value reflect.Value) {
		walk(value.Interface(), fn)
	}

	switch val.Kind() {
	case reflect.String:
		fn(val.String())
	case reflect.Struct:
		for i := 0; i < val.NumField(); i++ {
			walkValue(val.Field(i))
		}
	case reflect.Slice, reflect.Array:
		for i := 0; i < val.Len(); i++ {
			walkValue(val.Index(i))
		}
	case reflect.Map:
		for _, key := range val.MapKeys() {
			walkValue(val.MapIndex(key))
		}
	case reflect.Chan:
		for v, ok := val.Recv(); ok; v, ok = val.Recv() {
			walkValue(v)
		}
	case reflect.Func:
		valFnResult := val.Call(nil)
		for _, res := range valFnResult {
			walkValue(res)
		}
	}
}
```

## Подведение итогов

- Представили некоторые концепции из пакета `reflect`.
- Использовали рекурсию для обхода произвольных структур данных.
- Сделали, оглядываясь назад, не очень удачный рефакторинг, но не слишком расстроились по этому поводу. Работая итеративно с тестами, это не такая уж большая проблема.
- Это затронуло лишь небольшой аспект рефлексии. [В блоге Go есть отличная статья, охватывающая более подробную информацию](https://blog.golang.org/laws-of-reflection).
- Теперь, когда вы знаете о рефлексии, постарайтесь избегать ее использования.