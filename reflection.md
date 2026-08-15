# Рефлексия

**[Весь код для этой главы вы найдете здесь](https://github.com/quii/learn-go-with-tests/tree/main/reflection)**

[Из Твиттера](https://twitter.com/peterbourgon/status/1011403901419937792?s=09)

> golang challenge: напишите функцию `walk(x interface{}, fn func(string))`, которая принимает структуру `x` и вызывает `fn` для всех строковых полей, найденных внутри. Уровень сложности: рекурсивно.

Для этого нам понадобится использовать _рефлексию_.

> Рефлексия в вычислительной технике — это способность программы исследовать свою собственную структуру, в частности, через типы; это форма метапрограммирования. Это также большой источник путаницы.

Из [Блога Go: Reflection](https://blog.golang.org/laws-of-reflection)

## Что такое `interface{}`?

Мы наслаждались типобезопасностью, которую Go предлагал нам в виде функций, работающих с известными типами, такими как `string`, `int` и нашими собственными типами, например `BankAccount`.

Это означает, что мы получаем некоторую документацию бесплатно, и компилятор будет жаловаться, если вы попытаетесь передать функции неправильный тип.

Однако вы можете столкнуться со сценариями, когда вы хотите написать функцию, тип которой вы не знаете во время компиляции.

Go позволяет нам обойти это с помощью типа `interface{}`, который можно рассматривать как _любой_ тип (на самом деле, в Go `any` является [псевдонимом](https://cs.opensource.google/go/go/+/master:src/builtin/builtin.go;drc=master;l=95) для `interface{}`).

Таким образом, `walk(x interface{}, fn func(string))` примет любое значение для `x`.

### Так почему бы не использовать `interface{}` для всего и не иметь действительно гибких функций?

-   Как пользователь функции, которая принимает `interface{}`, вы теряете типобезопасность. Что, если вы хотели передать `Herd.species` типа `string` в функцию, но вместо этого передали `Herd.count`, который является `int`? Компилятор не сможет сообщить вам о вашей ошибке. Вы также понятия не имеете, _что_ вам разрешено передавать функции. Знание того, что функция принимает `UserService`, например, очень полезно.
-   Как автор такой функции, вы должны быть в состоянии проверять _все_, что было вам передано, и пытаться выяснить, какой это тип и что вы можете с ним сделать. Это делается с помощью _рефлексии_. Это может быть довольно неуклюже и трудно читаемо, и, как правило, менее производительно (поскольку вам приходится выполнять проверки во время выполнения).

Короче говоря, используйте рефлексию только в том случае, если она вам действительно необходима.

Если вы хотите полиморфные функции, подумайте, можете ли вы спроектировать их вокруг интерфейса (не `interface{}`, что сбивает с толку), чтобы пользователи могли использовать вашу функцию с несколькими типами, если они реализуют любые методы, необходимые для работы вашей функции.

Наша функция должна будет работать со многими различными вещами. Как всегда, мы будем использовать итеративный подход, написав тесты для каждого нового элемента, который мы хотим поддерживать, и рефакторинг по пути, пока не закончим.

## Сначала напишите тест

Мы хотим вызвать нашу функцию со структурой, которая содержит строковое поле (`x`). Затем мы можем проследить за переданной функцией (`fn`), чтобы убедиться, что она была вызвана.

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

-   Мы хотим хранить срез строк (`got`), который сохраняет, какие строки были переданы в `fn` функцией `walk`. Часто в предыдущих главах мы создавали для этого специальные типы для шпионажа за вызовами функций/методов, но в данном случае мы можем просто передать анонимную функцию для `fn`, которая замыкается на `got`.
-   Мы используем анонимную **структуру** с полем `Name` строкового типа, чтобы пойти по простейшему "счастливому" пути.
-   Наконец, вызовите `walk` с `x` и шпионом, и пока просто проверьте длину `got`; мы будем более конкретны в наших утверждениях, как только у нас заработает что-то очень простое.

## Попробуйте запустить тест

```
./reflection_test.go:21:2: undefined: walk
```

## Напишите минимальный объем кода, чтобы тест запустился, и проверьте вывод неудачного теста

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

## Напишите достаточно кода, чтобы тест прошел

Мы можем вызвать шпиона с любой строкой, чтобы тест прошел.

```go
func walk(x interface{}, fn func(input string)) {
	fn("I still can't believe South Korea beat Germany 2-0 to put them last in their group")
}
```

Теперь тест должен проходить. Следующее, что нам нужно будет сделать, это более точно указать, с чем вызывается наша `fn`.

## Сначала напишите тест

Добавьте следующее в существующий тест, чтобы проверить правильность строки, переданной в `fn`:

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

## Напишите достаточно кода, чтобы тест прошел

```go
func walk(x interface{}, fn func(input string)) {
	val := reflect.ValueOf(x)
	field := val.Field(0)
	fn(field.String())
}
```

Этот код _очень небезопасен и очень наивен_, но помните: наша цель, когда мы находимся в "красной" зоне (тесты не проходят), — написать как можно меньше кода. Затем мы пишем больше тестов, чтобы решить наши проблемы.

Нам нужно использовать рефлексию, чтобы заглянуть в `x` и попытаться изучить его свойства.

Пакет [reflect](https://pkg.go.dev/reflect) содержит функцию `ValueOf`, которая возвращает нам `Value` для данной переменной. У нее есть способы для нас инспектировать значение, включая его поля, которые мы используем в следующей строке.

Затем мы делаем несколько очень оптимистичных предположений о переданном значении:

-   Мы смотрим на первое и единственное поле. Однако полей может не быть вовсе, что вызовет панику.
-   Затем мы вызываем `String()`, которая возвращает базовое значение в виде строки. Однако это было бы неправильно, если бы поле было чем-то иным, чем строка.

## Рефакторинг

Наш код проходит для простого случая, но мы знаем, что у него много недостатков.

Мы собираемся написать ряд тестов, в которых мы передаем различные значения и проверяем срез строк, с которыми была вызвана `fn`.

Мы должны рефакторить наш тест в табличный тест, чтобы упростить дальнейшее тестирование новых сценариев.

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

## Напишите достаточно кода, чтобы тест прошел

```go
func walk(x interface{}, fn func(input string)) {
	val := reflect.ValueOf(x)

	for i := 0; i < val.NumField(); i++ {
		field := val.Field(i)
		fn(field.String())
	}
}
```

У `val` есть метод `NumField`, который возвращает количество полей в значении. Это позволяет нам итерироваться по полям и вызывать `fn`, что проходит наш тест.

## Рефакторинг

Похоже, здесь нет очевидных рефакторингов, которые улучшили бы код, так что продолжим.

Следующий недостаток в `walk` заключается в том, что он предполагает, что каждое поле является `string`. Давайте напишем тест для этого сценария.

## Сначала напишите тест

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

## Попробуйте запустить тест

```
=== RUN   TestWalk/struct_with_non_string_field
    --- FAIL: TestWalk/struct_with_non_string_field (0.00s)
        reflection_test.go:46: got [Chris <int Value>], want [Chris]
```

## Напишите достаточно кода, чтобы тест прошел

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

Мы можем сделать это, проверив его [`Kind`](https://pkg.go.dev/reflect#Kind).

## Рефакторинг

Снова, похоже, что код достаточно приемлем на данный момент.

Следующий сценарий: что, если это не "плоская" **структура**? Другими словами, что произойдет, если у нас будет **структура** с некоторыми вложенными полями?

## Сначала напишите тест

Мы использовали синтаксис анонимной **структуры** для объявления типов на ходу для наших тестов, поэтому мы могли бы продолжить это делать следующим образом:

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

Но мы видим, что когда вы получаете вложенные анонимные **структуры**, синтаксис становится немного запутанным. [Есть предложение сделать синтаксис более приятным](https://github.com/golang/go/issues/12854).

Давайте просто рефакторить это, создав известный тип для этого сценария и ссылаясь на него в тесте. Есть небольшая косвенность в том, что часть кода для нашего теста находится вне теста, но читатели должны быть в состоянии понять структуру **структуры**, глядя на инициализацию.

Добавьте следующие объявления типов где-нибудь в файле вашего теста:

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

Теперь мы можем добавить это в наши `cases`, что читается намного понятнее, чем раньше:

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

Проблема в том, что мы итерируемся только по полям на первом уровне иерархии типа.

## Напишите достаточно кода, чтобы тест прошел

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

Решение довольно простое: мы снова проверяем его `Kind`, и если оно оказывается **структурой**, мы просто снова вызываем `walk` для этой внутренней **структуры**.

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

Когда вы сравниваете одно и то же значение более одного раза, _как правило_, рефакторинг в `switch` улучшит читаемость и облегчит расширение вашего кода.

Что, если значение переданной **структуры** является **указателем**?

## Сначала напишите тест

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

## Попробуйте запустить тест

```
=== RUN   TestWalk/pointers_to_things
panic: reflect: call of reflect.Value.NumField on ptr Value [recovered]
    panic: reflect: call of reflect.Value.NumField on ptr Value
```

## Напишите достаточно кода, чтобы тест прошел

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

Вы не можете использовать `NumField` на `Value` типа **указатель**; нам нужно извлечь базовое значение, прежде чем мы сможем это сделать, используя `Elem()`.

## Рефакторинг

Давайте инкапсулируем ответственность по извлечению `reflect.Value` из данного `interface{}` в функцию.

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

-   Получить `reflect.Value` от `x`, чтобы я мог его инспектировать, мне не важно, как.
-   Итерироваться по полям, делая то, что необходимо в зависимости от их типа.

Далее нам нужно рассмотреть **срезы**.

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

## Напишите минимальный объем кода, чтобы тест запустился, и проверьте вывод неудачного теста

Это похоже на предыдущий сценарий с **указателем**: мы пытаемся вызвать `NumField` для нашего `reflect.Value`, но у него его нет, так как это не **структура**.

## Напишите достаточно кода, чтобы тест прошел

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

Это работает, но выглядит не очень. Не беда, у нас есть рабочий код, подкрепленный тестами, поэтому мы можем изменять его сколько угодно.

Если немного абстрагироваться, мы хотим вызвать `walk` либо для:

-   Каждого поля в **структуре**
-   Каждого _элемента_ в **срезе**

Наш текущий код делает это, но не очень хорошо отражает. У нас просто есть проверка в начале, чтобы увидеть, является ли это **срезом** (с `return`, чтобы остановить выполнение остального кода), и если нет, мы просто предполагаем, что это **структура**.

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

Выглядит намного лучше! Если это **структура** или **срез**, мы итерируемся по ее значениям, вызывая `walk` для каждого из них. В противном случае, если это `reflect.String`, мы можем вызвать `fn`.

Тем не менее, мне кажется, что это могло бы быть лучше. Есть повторение операции итерирования по полям/значениям и затем вызова `walk`, но концептуально они одинаковы.

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

Если `value` — это `reflect.String`, то мы просто вызываем `fn`, как обычно.

В противном случае наш `switch` извлечет две вещи в зависимости от типа:

-   Сколько полей
-   Как извлечь `Value` (`Field` или `Index`)

Как только мы определили эти вещи, мы можем итерироваться по `numberOfValues`, вызывая `walk` с результатом функции `getField`.

Теперь, когда мы это сделали, обработка массивов должна быть тривиальной.

## Сначала напишите тест

Добавьте в `cases`

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

## Напишите достаточно кода, чтобы тест прошел

Массивы могут быть обработаны так же, как и **срезы**, поэтому просто добавьте его в `case` через запятую.

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

## Напишите достаточно кода, чтобы тест прошел

Опять же, если немного абстрагироваться, можно увидеть, что `map` очень похож на **структуру**, просто ключи неизвестны во время компиляции.

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

Однако по замыслу невозможно получить значения из `map` по индексу. Это делается только по _ключу_, так что это нарушает нашу абстракцию, черт возьми.

## Рефакторинг

Как вы себя сейчас чувствуете? Тогда это казалось неплохой абстракцией, но теперь код кажется немного шатким.

_Это нормально!_ Рефакторинг — это путешествие, и иногда мы будем совершать ошибки. Главный смысл TDD в том, что он дает нам свободу пробовать такие вещи.

Делая небольшие шаги, подкрепленные тестами, это ни в коем случае не необратимая ситуация. Давайте просто вернемся к тому, как было до рефакторинга.

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

Помните, что `map` в Go не гарантируют порядок. Поэтому ваши тесты иногда будут завершаться неудачно, потому что мы утверждаем, что вызовы `fn` выполняются в определенном порядке.

Чтобы это исправить, нам нужно перенести наше утверждение с `map` в новый тест, где порядок не имеет значения.

```go
t.Run("with maps", func(t *testing.T) {
	aMap := map[string]string{
		"Cow": "Moo",
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

Поскольку мы вынесли `map` в отдельный тест, мы не видели сообщение об ошибке. Намеренно сломайте тест `with maps` здесь, чтобы вы могли проверить сообщение об ошибке, а затем снова исправьте его, чтобы все тесты проходили.

Мы отказались от проверки _порядка_ `got`, потому что `map` его не гарантируют, но это не означает, что мы должны отказаться от проверки всего, что касается его формы. Один только `assertContains` все равно прошел бы, если бы `walk` посетил элемент `map` дважды или пропустил его и проверил только оставшиеся записи — до тех пор, пока искомые значения присутствуют где-то, сколько бы раз это ни было. В отличие от порядка, _длина_ `got` полностью предсказуема независимо от того, в каком порядке итерируется `map`, поэтому давайте также проверим это.

```go
func assertLength(t testing.TB, got []string, want int) {
	t.Helper()
	if len(got) != want {
		t.Errorf("got %d values but expected %d", len(got), want)
	}
}
```

Добавьте вызов этой функции в начало теста `with maps`.

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

## Напишите достаточно кода, чтобы тест прошел

Мы можем итерироваться по всем значениям, отправленным через канал, пока он не будет закрыт с помощью `Recv()`.

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

## Напишите достаточно кода, чтобы тест прошел

Функции с ненулевым числом аргументов не кажутся очень осмысленными в этом сценарии. Но мы должны разрешить произвольные возвращаемые значения.

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

## В заключение

-   Представлены некоторые концепции из пакета `reflect`.
-   Использована рекурсия для обхода произвольных структур данных.
-   Выполнен, оглядываясь назад, неудачный рефакторинг, но не сильно расстроились по этому поводу. Работая итеративно с тестами, это не такая уж большая проблема.
-   Это охватило лишь небольшой аспект рефлексии. [В блоге Go есть отличная статья, более подробно раскрывающая эту тему](https://blog.golang.org/laws-of-reflection).
-   Теперь, когда вы знаете о рефлексии, постарайтесь максимально избегать ее использования.