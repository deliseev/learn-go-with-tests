# Рефлексия

**[Весь код для этой главы вы найдете здесь](https://github.com/quii/learn-go-with-tests/tree/main/reflection)**

[Из Твиттера](https://twitter.com/peterbourgon/status/1011403901419937792?s=09)

> Челлендж по golang: напишите функцию `walk(x interface{}, fn func(string))`, которая принимает структуру `x` и вызывает `fn` для всех строковых полей, найденных внутри. Уровень сложности: рекурсивно.

Для этого нам понадобится использовать _рефлексию_.

> Рефлексия в программировании — это способность программы исследовать собственную структуру, в частности, через типы; это форма метапрограммирования. Это также является источником большого количества путаницы.

Из [Блога Go: Рефлексия](https://blog.golang.org/laws-of-reflection)

## Что такое `interface{}`?

Мы наслаждались типовой безопасностью, которую Go предлагает нам в виде функций, работающих с известными типами, такими как `string`, `int` и нашими собственными типами, например `BankAccount`.

Это означает, что мы получаем некоторую документацию бесплатно, и компилятор будет жаловаться, если вы попытаетесь передать функции неверный тип.

Однако вы можете столкнуться со сценариями, когда вы хотите написать функцию, в которой тип неизвестен во время компиляции.

Go позволяет нам обойти это с помощью типа `interface{}`, который можно рассматривать просто как _любой_ тип (на самом деле, в Go `any` является [псевдонимом](https://cs.opensource.google/go/go/+/master:src/builtin/builtin.go;drc=master;l=95) для `interface{}`).

Таким образом, `walk(x interface{}, fn func(string))` примет любое значение для `x`.

### Так почему бы не использовать `interface{}` для всего и не иметь действительно гибкие функции?

- Как пользователь функции, которая принимает `interface{}`, вы теряете типовую безопасность. Что, если вы хотели передать `Herd.species` типа `string` в функцию, но вместо этого передали `Herd.count`, который является `int`? Компилятор не сможет сообщить вам о вашей ошибке. Вы также понятия не имеете, _что_ вам разрешено передавать в функцию. Например, знание того, что функция принимает `UserService`, очень полезно.
- Как автор такой функции, вы должны иметь возможность инспектировать _что угодно_, что вам было передано, и пытаться выяснить, что это за тип и что вы можете с ним делать. Это делается с помощью _рефлексии_. Это может быть довольно громоздким и трудночитаемым, и, как правило, менее производительным (поскольку вам приходится выполнять проверки во время выполнения).

Коротко: используйте рефлексию, только если это действительно необходимо.

Если вы хотите полиморфные функции, подумайте, можете ли вы спроектировать их вокруг интерфейса (не `interface{}`, что может сбивать с толку), чтобы пользователи могли использовать вашу функцию с несколькими типами, если они реализуют необходимые методы для работы вашей функции.

Наша функция должна будет работать со множеством различных вещей. Как всегда, мы будем использовать итеративный подход, писать тесты для каждой новой функциональности, которую мы хотим поддержать, и рефакторить по ходу дела, пока не закончим.

## Сначала напишите тест

Мы захотим вызвать нашу функцию со структурой, содержащей строковое поле (`x`). Затем мы сможем "шпионить" за переданной функцией (`fn`), чтобы проверить, вызывается ли она.

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

- Мы хотим хранить срез строк (`got`), который сохраняет, какие строки были переданы в `fn` функцией `walk`. Часто в предыдущих главах мы создавали для этого специальные типы, чтобы шпионить за вызовами функций/методов, но в данном случае мы можем просто передать анонимную функцию для `fn`, которая замыкается над `got`.
- Мы используем анонимную `struct` со строковым полем `Name`, чтобы пойти по простейшему "счастливому" пути.
- Наконец, вызовите `walk` с `x` и шпионом, и пока просто проверьте длину `got`; мы будем более конкретны с нашими утверждениями, как только у нас заработает что-то очень простое.

## Попробуйте запустить тест

```
./reflection_test.go:21:2: undefined: walk
```

## Напишите минимальный объем кода для запуска теста и проверьте вывод ошибочного теста

Нам нужно определить `walk`.

```go
func walk(x interface{}, fn func(input string)) {

}
```

Попробуйте запустить тест снова.

```
=== RUN   TestWalk
--- FAIL: TestWalk (0.00s)
    reflection_test.go:19: wrong number of function calls, got 0 want 1
FAIL
```

## Напишите достаточный объем кода, чтобы тест прошел

Мы можем вызвать шпиона с любой строкой, чтобы тест прошел.

```go
func walk(x interface{}, fn func(input string)) {
	fn("I still can't believe South Korea beat Germany 2-0 to put them last in their group")
}
```

Теперь тест должен проходить. Следующее, что нам нужно будет сделать, это более конкретное утверждение о том, с чем вызывается наша `fn`.

## Сначала напишите тест

Добавьте следующее к существующему тесту, чтобы проверить, что строка, переданная в `fn`, верна.

```go
if got[0] != expected {
	t.Errorf("got %q, want %q", got[0], expected)
}
```

## Попробуйте запустить тест

```
=== RUN   TestWalk
--- FAIL: TestWalk (0.00s)
    reflection_test.go:23: got 'I still can't believe South Korea beat Germany 2-0 to put them last in their group', want 'Chris'
FAIL
```

## Напишите достаточный объем кода, чтобы тест прошел

```go
func walk(x interface{}, fn func(input string)) {
	val := reflect.ValueOf(x)
	field := val.Field(0)
	fn(field.String())
}
```

Этот код _очень небезопасен и очень наивен_, но помните: наша цель, когда мы находимся в "красной" зоне (тесты не проходят), — написать наименьшее возможное количество кода. Затем мы пишем больше тестов для решения наших проблем.

Нам нужно использовать рефлексию, чтобы посмотреть на `x` и попытаться изучить его свойства.

Пакет [reflect](https://pkg.go.dev/reflect) имеет функцию `ValueOf`, которая возвращает нам `Value` данной переменной. Она предоставляет способы для инспектирования значения, включая его поля, которые мы используем в следующей строке.

Затем мы делаем несколько очень оптимистичных предположений о переданном значении:

- Мы смотрим на первое и единственное поле. Однако полей может не быть вообще, что вызовет панику.
- Затем мы вызываем `String()`, которая возвращает базовое значение в виде строки. Однако это было бы неверно, если бы поле было чем-то иным, чем строка.

## Рефакторинг

Наш код проходит для простого случая, но мы знаем, что он имеет много недостатков.

Мы собираемся написать несколько тестов, где мы будем передавать различные значения и проверять срез строк, с которыми была вызвана `fn`.

Мы должны переработать наш тест в табличный тест, чтобы упростить дальнейшее тестирование новых сценариев.

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

## Сначала напишите тест

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

## Попробуйте запустить тест

```
=== RUN   TestWalk/struct_with_two_string_fields
    --- FAIL: TestWalk/struct_with_two_string_fields (0.00s)
        reflection_test.go:40: got [Chris], want [Chris London]
```

## Напишите достаточный объем кода, чтобы тест прошел

```go
func walk(x interface{}, fn func(input string)) {
	val := reflect.ValueOf(x)

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)
		fn(field.String())
	}
}
```

У `val` есть метод `NumField`, который возвращает количество полей в значении. Это позволяет нам итерировать поля и вызывать `fn`, что приводит к прохождению нашего теста.

## Рефакторинг

Похоже, здесь нет очевидных рефакторингов, которые улучшили бы код, так что давайте продолжим.

Следующий недостаток в `walk` заключается в том, что она предполагает, что каждое поле является `string`. Давайте напишем тест для этого сценария.

## Сначала напишите тест

Добавьте следующий случай:

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

## Попробуйте запустить тест

```
=== RUN   TestWalk/struct_with_non_string_field
    --- FAIL: TestWalk/struct_with_non_string_field (0.00s)
        reflection_test.go:46: got [Chris <int Value>], want [Chris]
```

## Напишите достаточный объем кода, чтобы тест прошел

Нам нужно убедиться, что тип поля — `string`.

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

Мы можем сделать это, проверив его [`Kind`](https://pkg.go.dev/reflect#Kind).

## Рефакторинг

Снова, похоже, код достаточно разумный на данный момент.

Следующий сценарий: что, если это не "плоская" `struct`? Другими словами, что произойдет, если у нас есть `struct` с вложенными полями?

## Сначала напишите тест

Мы использовали синтаксис анонимных структур для объявления типов ad-hoc для наших тестов, поэтому мы могли бы продолжить делать это так:

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

Но мы видим, что при использовании внутренних анонимных структур синтаксис становится немного запутанным. [Существует предложение сделать синтаксис более приятным](https://github.com/golang/go/issues/12854).

Давайте просто переделаем это, создав известный тип для этого сценария и сославшись на него в тесте. Здесь есть небольшая косвенность в том смысле, что часть кода для нашего теста находится вне теста, но читатели должны иметь возможность понять структуру `struct`, взглянув на инициализацию.

Добавьте следующие объявления типов где-нибудь в ваш тестовый файл:

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

Теперь мы можем добавить это к нашим сценариям, что читается намного яснее, чем раньше:

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

## Попробуйте запустить тест

```
=== RUN   TestWalk/Nested_fields
    --- FAIL: TestWalk/nested_fields (0.00s)
        reflection_test.go:54: got [Chris], want [Chris London]
```

Проблема в том, что мы итерируем только поля на первом уровне иерархии типа.

## Напишите достаточный объем кода, чтобы тест прошел

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

Решение довольно простое: мы снова проверяем его `Kind`, и если оно оказывается `struct`, мы просто снова вызываем `walk` для этой внутренней `struct`.

## Рефакторинг

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

Когда вы сравниваете одно и то же значение более одного раза, _обычно_ рефакторинг в `switch` улучшит читаемость и сделает ваш код проще для расширения.

Что, если значение переданной структуры является указателем?

## Сначала напишите тест

Добавьте этот случай:

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

## Попробуйте запустить тест

```
=== RUN   TestWalk/pointers_to_things
panic: reflect: call of reflect.Value.NumField on ptr Value [recovered]
    panic: reflect: call of reflect.Value.NumField on ptr Value
```

## Напишите достаточный объем кода, чтобы тест прошел

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

Вы не можете использовать `NumField` на `Value` указателя; нам нужно извлечь базовое значение, прежде чем мы сможем это сделать, используя `Elem()`.

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

Это фактически добавляет _больше_ кода, но я считаю, что уровень абстракции правильный.

- Получить `reflect.Value` от `x`, чтобы я мог его инспектировать, мне не важно, как.
- Итерировать поля, выполняя все, что необходимо, в зависимости от их типа.

Далее нам нужно рассмотреть срезы.

## Сначала напишите тест

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

## Попробуйте запустить тест

```
=== RUN   TestWalk/slices
panic: reflect: call of reflect.Value.NumField on slice Value [recovered]
    panic: reflect: call of reflect.Value.NumField on slice Value
```

## Напишите минимальный объем кода для запуска теста и проверьте вывод ошибочного теста

Это похоже на предыдущий сценарий с указателем: мы пытаемся вызвать `NumField` на нашем `reflect.Value`, но у него нет такого метода, так как это не структура.

## Напишите достаточный объем кода, чтобы тест прошел

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

Это работает, но выглядит не очень. Не волнуйтесь, у нас есть рабочий код, поддерживаемый тестами, так что мы можем экспериментировать сколько угодно.

Если мыслить немного абстрактно, мы хотим вызвать `walk` либо:

- На каждое поле в структуре
- На каждую _вещь_ в срезе

Наш текущий код делает это, но не очень хорошо отражает. У нас просто есть проверка в начале, чтобы увидеть, является ли это срезом (с `return`, чтобы остановить выполнение остального кода), и если нет, мы просто предполагаем, что это структура.

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

Выглядит гораздо лучше! Если это структура или срез, мы итерируем его значения, вызывая `walk` для каждого из них. В противном случае, если это `reflect.String`, мы можем вызвать `fn`.

Все же, мне кажется, что могло бы быть лучше. Повторяется операция итерации по полям/значениям, а затем вызов `walk`, но концептуально они одинаковы.

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

- Сколько полей есть
- Как извлечь `Value` (`Field` или `Index`)

Как только мы определили эти вещи, мы можем итерировать `numberOfValues`, вызывая `walk` с результатом функции `getField`.

Теперь, когда мы это сделали, обработка массивов должна быть тривиальной.

## Сначала напишите тест

Добавьте в сценарии:

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

## Попробуйте запустить тест

```
=== RUN   TestWalk/arrays
    --- FAIL: TestWalk/arrays (0.00s)
        reflection_test.go:78: got [], want [London Reykjavík]
```

## Напишите достаточный объем кода, чтобы тест прошел

Массивы могут быть обработаны так же, как и срезы, поэтому просто добавьте их к случаю через запятую:

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

Следующий тип, который мы хотим обработать, это `map`.

## Сначала напишите тест

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

## Попробуйте запустить тест

```
=== RUN   TestWalk/maps
    --- FAIL: TestWalk/maps (0.00s)
        reflection_test.go:86: got [], want [Moo Baa]
```

## Напишите достаточный объем кода, чтобы тест прошел

Опять же, если вы мыслите немного абстрактно, вы можете увидеть, что `map` очень похожа на `struct`; просто ключи неизвестны во время компиляции.

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

Однако по задумке вы не можете получить значения из map по индексу. Это делается только по _ключу_, так что это нарушает нашу абстракцию, черт возьми.

## Рефакторинг

Как вы себя чувствуете сейчас? Тогда это казалось хорошей абстракцией, но теперь код выглядит немного странно.

_Это нормально!_ Рефакторинг — это путешествие, и иногда мы совершаем ошибки. Главный смысл TDD в том, что он дает нам свободу пробовать что-то новое.

Делая небольшие шаги, подкрепленные тестами, мы ни в коем случае не попадаем в необратимую ситуацию. Давайте просто вернем код к тому виду, в котором он был до рефакторинга.

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

### Последняя проблема

Помните, что `map` в Go не гарантируют порядок. Поэтому ваши тесты иногда будут падать, потому что мы утверждаем, что вызовы `fn` выполняются в определенном порядке.

Чтобы исправить это, нам нужно будет перенести наше утверждение с `map` в новый тест, где нам не важен порядок.

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

Вот как определяется `assertContains`:

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

Поскольку мы вынесли `map` в новый тест, мы не видели сообщения об ошибке. Намеренно сломайте тест `with maps` здесь, чтобы вы могли проверить сообщение об ошибке, а затем снова исправьте его, чтобы все тесты проходили.

Мы отказались от проверки _порядка_ `got`, потому что `map` не гарантируют его, но это не означает, что мы должны отказаться от проверки всего, что касается их формы. `assertContains` сам по себе все равно прошел бы, если бы `walk` посетил элемент `map` дважды или пропустил один и проверил только оставшиеся элементы — до тех пор, пока конкретные значения, которые мы ищем, присутствуют где-либо, сколько бы раз это ни было. В отличие от порядка, _длина_ `got` полностью предсказуема независимо от того, в каком порядке итерируется `map`, поэтому давайте также сделаем утверждение об этом.

```go
func assertLength(t testing.TB, got []string, want int) {
	t.Helper()
	if len(got) != want {
		t.Errorf("got %d values but expected %d", len(got), want)
	}
}
```

Добавьте вызов к ней в начале теста `with maps`.

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

	assertLength(t, got, len(aMap))
	assertContains(t, got, "Moo")
	assertContains(t, got, "Baa")
})
```

Следующий тип, который мы хотим обработать, это `chan`.

## Сначала напишите тест

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

## Попробуйте запустить тест

```
--- FAIL: TestWalk (0.00s)
    --- FAIL: TestWalk/with_channels (0.00s)
        reflection_test.go:115: got [], want [Berlin Katowice]
```

## Напишите достаточный объем кода, чтобы тест прошел

Мы можем итерировать все значения, отправленные через канал, пока он не будет закрыт с помощью `Recv()`.

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
Следующий тип, который мы хотим обработать, это `func`.

## Сначала напишите тест

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

## Попробуйте запустить тест

```
--- FAIL: TestWalk (0.00s)
    --- FAIL: TestWalk/with_function (0.00s)
        reflection_test.go:132: got [], want [Berlin Katowice]
```

## Напишите достаточный объем кода, чтобы тест прошел

Функции без аргументов не кажутся очень осмысленными в этом сценарии. Но мы должны предусмотреть произвольные возвращаемые значения.

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

## Подводим итоги

- Представили некоторые концепции из пакета `reflect`.
- Использовали рекурсию для обхода произвольных структур данных.
- Сделали, оглядываясь назад, неудачный рефакторинг, но не слишком расстроились по этому поводу. Работая итеративно с тестами, это не такая уж большая проблема.
- Это охватило лишь небольшой аспект рефлексии. [В блоге Go есть отличный пост, охватывающий больше деталей](https://blog.golang.org/laws-of-reflection).
- Теперь, когда вы знаете о рефлексии, постарайтесь максимально избегать ее использования.