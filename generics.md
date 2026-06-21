# Обобщения

**[Весь код для этой главы можно найти здесь](https://github.com/quii/learn-go-with-tests/tree/main/generics)**

Эта глава познакомит вас с обобщениями (generics), развеет возможные предубеждения и даст представление о том, как упростить часть вашего кода в будущем. Прочитав ее, вы узнаете, как писать:

- Функцию, которая принимает обобщенные аргументы
- Обобщенную структуру данных

## Наши собственные вспомогательные функции для тестов (`AssertEqual`, `AssertNotEqual`)

Чтобы изучить обобщения, мы напишем несколько вспомогательных функций для тестов.

### Проверка для целых чисел

Начнем с чего-то простого и будем двигаться к нашей цели.

```go
import "testing"

func TestAssertFunctions(t *testing.T) {
	t.Run("asserting on integers", func(t *testing.T) {
		AssertEqual(t, 1, 1)
		AssertNotEqual(t, 1, 2)
	})
}

func AssertEqual(t *testing.T, got, want int) {
	t.Helper()
	if got != want {
		t.Errorf("got %d, want %d", got, want)
	}
}

func AssertNotEqual(t *testing.T, got, want int) {
	t.Helper()
	if got == want {
		t.Errorf("didn't want %d", got)
	}
}
```

### Проверка для строк

Возможность проверять равенство целых чисел — это отлично, но что, если мы захотим проверить `string`?

```go
t.Run("asserting on strings", func(t *testing.T) {
	AssertEqual(t, "hello", "hello")
	AssertNotEqual(t, "hello", "Grace")
})
```

Вы получите ошибку

```
# github.com/quii/learn-go-with-tests/generics [github.com/quii/learn-go-with-tests/generics.test]
./generics_test.go:12:18: cannot use "hello" (untyped string constant) as int value in argument to AssertEqual
./generics_test.go:13:21: cannot use "hello" (untyped string constant) as int value in argument to AssertNotEqual
./generics_test.go:13:30: cannot use "Grace" (untyped string constant) as int value in argument to AssertNotEqual
```

Если вы внимательно прочитаете ошибку, то увидите, что компилятор жалуется на то, что мы пытаемся передать `string` в функцию, которая ожидает `int`.

#### Краткое повторение о типобезопасности

Если вы читали предыдущие главы этой книги или имеете опыт работы со статически типизированными языками, это не должно вас удивлять. Компилятор Go ожидает, что вы будете писать свои функции, структуры и т.д., описывая, с какими типами вы хотите работать.

Вы не можете передать `string` в функцию, которая ожидает `int`.

Хотя это может показаться излишним, это может быть чрезвычайно полезно. Описывая эти ограничения, вы:

- Упрощаете реализацию функций. Описывая компилятору, с какими типами вы работаете, вы **ограничиваете количество возможных допустимых реализаций**. Вы не можете «сложить» `Person` и `BankAccount`. Вы не можете перевести в верхний регистр `int`. В разработке программного обеспечения ограничения часто бывают чрезвычайно полезны.
- Предотвращаете случайную передачу данных в функцию, которую вы не планировали.

Go предлагает вам способ быть более абстрактным с вашими типами с помощью [интерфейсов](./structs-methods-and-interfaces.md), чтобы вы могли разрабатывать функции, которые принимают не конкретные типы, а типы, предоставляющие необходимое поведение. Это дает вам некоторую гибкость при сохранении типобезопасности.

### Функция, которая принимает строку или целое число? (или, конечно, другие вещи)

Еще один вариант, который Go предлагает для повышения гибкости ваших функций, — это объявление типа аргумента как `interface{}`, что означает «что угодно».

Попробуйте изменить сигнатуры, чтобы использовать этот тип.

```go
func AssertEqual(got, want interface{})

func AssertNotEqual(got, want interface{})

```

Тесты теперь должны компилироваться и проходить. Если вы попробуете заставить их упасть, вы увидите, что вывод немного неаккуратный, потому что мы используем строку форматирования для целых чисел `%d` для печати наших сообщений, поэтому измените их на общий формат `%+v` для лучшего вывода любого типа значения.

### Проблема с `interface{}`

Наши функции `AssertX` довольно наивны, но концептуально не слишком отличаются от того, как эту функциональность предлагают другие [популярные библиотеки](https://github.com/matryer/is/blob/master/is.go#L150)

```go
func (is *I) Equal(a, b interface{})
```

Так в чем же проблема?

Используя `interface{}`, компилятор не может помочь нам при написании кода, потому что мы не сообщаем ему ничего полезного о типах вещей, передаваемых в функцию. Попробуйте сравнить два разных типа.

```go
AssertEqual(1, "1")
```

В этом случае нам это сходит с рук; тест компилируется и завершается неудачей, как мы и ожидали, хотя сообщение об ошибке `got 1, want 1` неясно; но хотим ли мы иметь возможность сравнивать строки с целыми числами? А как насчет сравнения `Person` с `Airport`?

Написание функций, которые принимают `interface{}`, может быть чрезвычайно сложным и подверженным ошибкам, потому что мы _потеряли_ наши ограничения, и у нас нет информации во время компиляции о том, с какими видами данных мы имеем дело.

Это означает, что **компилятор не может нам помочь**, и мы, скорее, столкнемся с **ошибками во время выполнения**, которые могут повлиять на наших пользователей, вызвать сбои или что-то похуже.

Часто разработчикам приходится использовать рефлексию для реализации этих *кхм* обобщенных функций, что может усложнить чтение и написание кода и ухудшить производительность вашей программы.

## Наши собственные вспомогательные функции для тестов с обобщениями

В идеале мы не хотим создавать отдельные функции `AssertX` для каждого типа, с которым мы когда-либо работаем. Мы хотели бы иметь _одну_ функцию `AssertEqual`, которая работает с _любым_ типом, но не позволяет сравнивать [яблоки с апельсинами](https://en.wikipedia.org/wiki/Apples_and_oranges).

Обобщения предлагают нам способ создавать абстракции (подобно интерфейсам), позволяя нам **описывать наши ограничения**. Они позволяют нам писать функции, которые имеют такой же уровень гибкости, как и `interface{}`, но при этом сохраняют типобезопасность и обеспечивают лучший опыт для вызывающих сторон.

```go
func TestAssertFunctions(t *testing.T) {
	t.Run("asserting on integers", func(t *testing.T) {
		AssertEqual(t, 1, 1)
		AssertNotEqual(t, 1, 2)
	})

	t.Run("asserting on strings", func(t *testing.T) {
		AssertEqual(t, "hello", "hello")
		AssertNotEqual(t, "hello", "Grace")
	})

	// AssertEqual(t, 1, "1") // uncomment to see the error
}

func AssertEqual[T comparable](t *testing.T, got, want T) {
	t.Helper()
	if got != want {
		t.Errorf("got %v, want %v", got, want)
	}
}

func AssertNotEqual[T comparable](t *testing.T, got, want T) {
	t.Helper()
	if got == want {
		t.Errorf("didn't want %v", got)
	}
}
```

Чтобы писать обобщенные функции в Go, вам необходимо предоставить «параметры типа», что является просто причудливым способом сказать «опишите свой обобщенный тип и дайте ему метку».

В нашем случае тип нашего параметра типа — `comparable`, и мы дали ему метку `T`. Эта метка затем позволяет нам описывать типы для аргументов нашей функции (`got, want T`).

Мы используем `comparable`, потому что хотим описать компилятору, что мы хотим использовать операторы `==` и `!=` для элементов типа `T` в нашей функции, мы хотим сравнивать! Если вы попробуете изменить тип на `any`,

```go
func AssertNotEqual[T any](got, want T)
```

Вы получите следующую ошибку:

```
prog.go2:15:5: cannot compare got != want (operator != not defined for T)
```

Что вполне логично, потому что вы не можете использовать эти операторы для каждого (или `any`) типа.

### Является ли обобщенная функция с [`T any`](https://go.googlesource.com/proposal/+/refs/heads/master/design/go2draft-type-parameters.md#the-constraint) такой же, как `interface{}`?

Рассмотрим две функции

```go
func GenericFoo[T any](x, y T)
```

```go
func InterfaceyFoo(x, y interface{})
```

В чем смысл обобщений здесь? Разве `any` не описывает... что угодно?

С точки зрения ограничений, `any` действительно означает «что угодно», как и `interface{}`. Фактически, `any` был добавлен в 1.18 и является _просто псевдонимом для `interface{}`_.

Разница с обобщенной версией заключается в том, что _вы все еще описываете конкретный тип_, и это означает, что мы по-прежнему ограничили эту функцию для работы только с _одним_ типом.

Это означает, что вы можете вызвать `InterfaceyFoo` с любой комбинацией типов (например, `InterfaceyFoo(apple, orange)`). Однако `GenericFoo` все еще предлагает некоторые ограничения, потому что мы сказали, что она работает только с _одним_ типом, `T`.

Допустимо:

- `GenericFoo(apple1, apple2)`
- `GenericFoo(orange1, orange2)`
- `GenericFoo(1, 2)`
- `GenericFoo("one", "two")`

Недопустимо (завершается ошибкой компиляции):

- `GenericFoo(apple1, orange1)`
- `GenericFoo("1", 1)`

Если ваша функция возвращает обобщенный тип, вызывающий код также может использовать этот тип в его первоначальном виде, вместо того чтобы выполнять утверждение типа, потому что когда функция возвращает `interface{}`, компилятор не может дать никаких гарантий относительно типа.

## Далее: Обобщенные типы данных

Мы собираемся создать тип данных [стек](https://en.wikipedia.org/wiki/Stack_(abstract_data_type)). Стеки должны быть довольно простыми для понимания с точки зрения требований. Это набор элементов, в который вы можете `Push` элементы на «вершину» и из которого вы можете `Pop` элементы с вершины (LIFO — последним вошел, первым вышел).

Для краткости я опустил процесс TDD, который привел меня к следующему коду для стека `int`ов и стека `string`ов.

```go
type StackOfInts struct {
	values []int
}

func (s *StackOfInts) Push(value int) {
	s.values = append(s.values, value)
}

func (s *StackOfInts) IsEmpty() bool {
	return len(s.values) == 0
}

func (s *StackOfInts) Pop() (int, bool) {
	if s.IsEmpty() {
		return 0, false
	}

	index := len(s.values) - 1
	el := s.values[index]
	s.values = s.values[:index]
	return el, true
}

type StackOfStrings struct {
	values []string
}

func (s *StackOfStrings) Push(value string) {
	s.values = append(s.values, value)
}

func (s *StackOfStrings) IsEmpty() bool {
	return len(s.values) == 0
}

func (s *StackOfStrings) Pop() (string, bool) {
	if s.IsEmpty() {
		return "", false
	}

	index := len(s.values) - 1
	el := s.values[index]
	s.values = s.values[:index]
	return el, true
}
```

Я создал пару других функций утверждения, чтобы помочь:

```go
func AssertTrue(t *testing.T, got bool) {
	t.Helper()
	if !got {
		t.Errorf("got %v, want true", got)
	}
}

func AssertFalse(t *testing.T, got bool) {
	t.Helper()
	if got {
		t.Errorf("got %v, want false", got)
	}
}
```

И вот тесты:

```go
func TestStack(t *testing.T) {
	t.Run("integer stack", func(t *testing.T) {
		myStackOfInts := new(StackOfInts)

		// check stack is empty
		AssertTrue(t, myStackOfInts.IsEmpty())

		// add a thing, then check it's not empty
		myStackOfInts.Push(123)
		AssertFalse(t, myStackOfInts.IsEmpty())

		// add another thing, pop it back again
		myStackOfInts.Push(456)
		value, _ := myStackOfInts.Pop()
		AssertEqual(t, value, 456)
		value, _ = myStackOfInts.Pop()
		AssertEqual(t, value, 123)
		AssertTrue(t, myStackOfInts.IsEmpty())
	})

	t.Run("string stack", func(t *testing.T) {
		myStackOfStrings := new(StackOfStrings)

		// check stack is empty
		AssertTrue(t, myStackOfStrings.IsEmpty())

		// add a thing, then check it's not empty
		myStackOfStrings.Push("123")
		AssertFalse(t, myStackOfStrings.IsEmpty())

		// add another thing, pop it back again
		myStackOfStrings.Push("456")
		value, _ := myStackOfStrings.Pop()
		AssertEqual(t, value, "456")
		value, _ = myStackOfStrings.Pop()
		AssertEqual(t, value, "123")
		AssertTrue(t, myStackOfStrings.IsEmpty())
	})
}
```

### Проблемы

- Код для `StackOfStrings` и `StackOfInts` почти идентичен. Хотя дублирование не всегда является концом света, это больше кода для чтения, написания и поддержки.
- Поскольку мы дублируем логику для двух типов, нам пришлось дублировать и тесты.

Мы действительно хотим воплотить _идею_ стека в одном типе и иметь один набор тестов для него. Сейчас нам следует надеть нашу "шляпу рефакторинга", что означает, что мы не должны изменять тесты, потому что мы хотим сохранить то же поведение.

Без обобщений мы _могли бы_ сделать следующее:

```go
type StackOfInts = Stack
type StackOfStrings = Stack

type Stack struct {
	values []interface{}
}

func (s *Stack) Push(value interface{}) {
	s.values = append(s.values, value)
}

func (s *Stack) IsEmpty() bool {
	return len(s.values) == 0
}

func (s *Stack) Pop() (interface{}, bool) {
	if s.IsEmpty() {
		var zero interface{}
		return zero, false
	}

	index := len(s.values) - 1
	el := s.values[index]
	s.values = s.values[:index]
	return el, true
}
```

- Мы делаем псевдонимы для наших предыдущих реализаций `StackOfInts` и `StackOfStrings` к новому унифицированному типу `Stack`.
- Мы удалили типобезопасность из `Stack`, сделав так, что `values` является [срезом](https://github.com/quii/learn-go-with-tests/blob/main/arrays-and-slices.md) `interface{}`.

Чтобы попробовать этот код, вам придется удалить ограничения типов из наших функций утверждения:

```go
func AssertEqual(t *testing.T, got, want interface{})
```

Если вы это сделаете, наши тесты все равно пройдут. Кому нужны обобщения?

### Проблема с отказом от типобезопасности

Первая проблема та же, что мы видели с нашей `AssertEquals` — мы потеряли типобезопасность. Теперь я могу `Push` яблоки в стек апельсинов.

Даже если у нас есть дисциплина не делать этого, с кодом все равно неприятно работать, потому что когда методы **возвращают `interface{}`, с ними ужасно работать**.

Добавьте следующий тест:

```go
t.Run("interface stack DX is horrid", func(t *testing.T) {
	myStackOfInts := new(StackOfInts)

	myStackOfInts.Push(1)
	myStackOfInts.Push(2)
	firstNum, _ := myStackOfInts.Pop()
	secondNum, _ := myStackOfInts.Pop()
	AssertEqual(t, firstNum+secondNum, 3)
})
```

Вы получаете ошибку компилятора, показывающую слабость потери типобезопасности:

```
invalid operation: operator + not defined on firstNum (variable of type interface{})
```

Когда `Pop` возвращает `interface{}`, это означает, что компилятор не имеет информации о том, что это за данные, и поэтому сильно ограничивает наши возможности. Он не может знать, что это должно быть целое число, поэтому не позволяет нам использовать оператор `+`.

Чтобы обойти это, вызывающий код должен выполнить [утверждение типа](https://golang.org/ref/spec#Type_assertions) для каждого значения.

```go
t.Run("interface stack dx is horrid", func(t *testing.T) {
	myStackOfInts := new(StackOfInts)

	myStackOfInts.Push(1)
	myStackOfInts.Push(2)
	firstNum, _ := myStackOfInts.Pop()
	secondNum, _ := myStackOfInts.Pop()

	// get our ints from out interface{}
	reallyFirstNum, ok := firstNum.(int)
	AssertTrue(t, ok) // need to check we definitely got an int out of the interface{}

	reallySecondNum, ok := secondNum.(int)
	AssertTrue(t, ok) // and again!

	AssertEqual(t, reallyFirstNum+reallySecondNum, 3)
})
```

Неприятность, исходящая от этого теста, будет повторяться для каждого потенциального пользователя нашей реализации `Stack`, фу.

### Обобщенные структуры данных приходят на помощь

Подобно тому, как вы можете определять обобщенные аргументы для функций, вы можете определять обобщенные структуры данных.

Вот наша новая реализация `Stack`, использующая обобщенный тип данных.

```go
type Stack[T any] struct {
	values []T
}

func (s *Stack[T]) Push(value T) {
	s.values = append(s.values, value)
}

func (s *Stack[T]) IsEmpty() bool {
	return len(s.values) == 0
}

func (s *Stack[T]) Pop() (T, bool) {
	if s.IsEmpty() {
		var zero T
		return zero, false
	}

	index := len(s.values) - 1
	el := s.values[index]
	s.values = s.values[:index]
	return el, true
}
```

Вот тесты, показывающие, как они работают так, как мы бы хотели, с полной типобезопасностью.

```go
func TestStack(t *testing.T) {
	t.Run("integer stack", func(t *testing.T) {
		myStackOfInts := new(Stack[int])

		// check stack is empty
		AssertTrue(t, myStackOfInts.IsEmpty())

		// add a thing, then check it's not empty
		myStackOfInts.Push(123)
		AssertFalse(t, myStackOfInts.IsEmpty())

		// add another thing, pop it back again
		myStackOfInts.Push(456)
		value, _ := myStackOfInts.Pop()
		AssertEqual(t, value, 456)
		value, _ = myStackOfInts.Pop()
		AssertEqual(t, value, 123)
		AssertTrue(t, myStackOfInts.IsEmpty())

		// can get the numbers we put in as numbers, not untyped interface{}
		myStackOfInts.Push(1)
		myStackOfInts.Push(2)
		firstNum, _ := myStackOfInts.Pop()
		secondNum, _ := myStackOfInts.Pop()
		AssertEqual(t, firstNum+secondNum, 3)
	})
}
```

Вы заметите, что синтаксис для определения обобщенных структур данных согласуется с определением обобщенных аргументов для функций.

```go
type Stack[T any] struct {
	values []T
}
```

Это _почти_ то же самое, что и раньше, просто мы говорим, что **тип стека ограничивает, с каким типом значений вы можете работать**.

Как только вы создадите `Stack[Orange]` или `Stack[Apple]`, методы, определенные для нашего стека, позволят вам передавать и возвращать только тот конкретный тип стека, с которым вы работаете:

```go
func (s *Stack[T]) Pop() (T, bool)
```

Вы можете представить, что типы реализации каким-то образом генерируются для вас, в зависимости от того, какой тип стека вы создаете:

```go
func (s *Stack[Orange]) Pop() (Orange, bool)
```

```go
func (s *Stack[Apple]) Pop() (Apple, bool)
```

Теперь, когда мы выполнили этот рефакторинг, мы можем безопасно удалить тест строкового стека, потому что нам не нужно снова и снова доказывать ту же логику.

Обратите внимание, что до сих пор в примерах вызова обобщенных функций нам не требовалось указывать обобщенные типы. Например, чтобы вызвать `AssertEqual[T]`, нам не нужно указывать, что такое тип `T`, так как его можно вывести из аргументов. В случаях, когда обобщенные типы не могут быть выведены, вам необходимо указывать типы при вызове функции. Синтаксис такой же, как при определении функции, то есть вы указываете типы внутри квадратных скобок перед аргументами.

В качестве конкретного примера рассмотрим создание конструктора для `Stack[T]`.
```go
func NewStack[T any]() *Stack[T] {
	return new(Stack[T])
}
```
Чтобы использовать этот конструктор, например, для создания стека целых чисел и стека строк, вы вызываете его следующим образом:
```go
myStackOfInts := NewStack[int]()
myStackOfStrings := NewStack[string]()
```

Ниже приведена реализация `Stack` и тесты после добавления конструктора.

```go
type Stack[T any] struct {
	values []T
}

func NewStack[T any]() *Stack[T] {
	return new(Stack[T])
}

func (s *Stack[T]) Push(value T) {
	s.values = append(s.values, value)
}

func (s *Stack[T]) IsEmpty() bool {
	return len(s.values) == 0
}

func (s *Stack[T]) Pop() (T, bool) {
	if s.IsEmpty() {
		var zero T
		return zero, false
	}

	index := len(s.values) - 1
	el := s.values[index]
	s.values = s.values[:index]
	return el, true
}
```

```go
func TestStack(t *testing.T) {
	t.Run("integer stack", func(t *testing.T) {
		myStackOfInts := NewStack[int]()

		// check stack is empty
		AssertTrue(t, myStackOfInts.IsEmpty())

		// add a thing, then check it's not empty
		myStackOfInts.Push(123)
		AssertFalse(t, myStackOfInts.IsEmpty())

		// add another thing, pop it back again
		myStackOfInts.Push(456)
		value, _ := myStackOfInts.Pop()
		AssertEqual(t, value, 456)
		value, _ = myStackOfInts.Pop()
		AssertEqual(t, value, 123)
		AssertTrue(t, myStackOfInts.IsEmpty())

		// can get the numbers we put in as numbers, not untyped interface{}
		myStackOfInts.Push(1)
		myStackOfInts.Push(2)
		firstNum, _ := myStackOfInts.Pop()
		secondNum, _ := myStackOfInts.Pop()
		AssertEqual(t, firstNum+secondNum, 3)
	})
}
```

Используя обобщенный тип данных, мы:

- Уменьшили дублирование важной логики.
- Сделали так, что `Pop` возвращает `T`, чтобы, если мы создаем `Stack[int]`, мы на практике получали `int` из `Pop`; теперь мы можем использовать `+` без необходимости в гимнастике с утверждением типа.
- Предотвратили неправильное использование во время компиляции. Вы не можете `Push` апельсины в стек яблок.

## Подведение итогов

Эта глава должна была дать вам представление о синтаксисе обобщений и некоторые идеи о том, почему обобщения могут быть полезны. Мы написали наши собственные функции `Assert`, которые мы можем безопасно повторно использовать для экспериментов с другими идеями, связанными с обобщениями, и реализовали простую структуру данных для хранения любого типа данных, который мы хотим, типобезопасным способом.

### Обобщения проще, чем использование `interface{}` в большинстве случаев

Если у вас мало опыта работы со статически типизированными языками, смысл обобщений может быть не сразу очевиден, но я надеюсь, что примеры в этой главе проиллюстрировали, где язык Go не так выразителен, как нам бы хотелось. В частности, использование `interface{}` делает ваш код:

- Менее безопасным (смешивание яблок и апельсинов), требует больше обработки ошибок
- Менее выразительным, `interface{}` ничего не говорит вам о данных
- Более склонным к использованию [рефлексии](https://github.com/quii/learn-go-with-tests/blob/main/reflection.md), утверждений типа и т.д., что затрудняет работу с кодом и делает его более подверженным ошибкам, поскольку переносит проверки со времени компиляции на время выполнения

Использование статически типизированных языков — это акт описания ограничений. Если вы делаете это хорошо, вы создаете код, который не только безопасен и прост в использовании, но и проще в написании, потому что пространство возможных решений меньше.

Обобщения дают нам новый способ выражения ограничений в нашем коде, что, как показано, позволит нам объединять и упрощать код, что было невозможно до 1.18.

### Превратят ли обобщения Go в Java?

- Нет.

В сообществе Go существует много [FUD (страха, неуверенности и сомнений)](https://en.wikipedia.org/wiki/Fear,_uncertainty,_and_doubt) по поводу того, что обобщения приведут к кошмарным абстракциям и запутанным кодовым базам. Обычно это сопровождается оговоркой: «их следует использовать осторожно».

Хотя это и верно, это не особенно полезный совет, потому что это справедливо для любой языковой особенности.

Немногие жалуются на нашу способность определять интерфейсы, которые, как и обобщения, являются способом описания ограничений в нашем коде. Когда вы описываете интерфейс, вы делаете дизайнерский выбор, который _может быть плохим_; обобщения не уникальны в своей способности создавать запутанный и неудобный в использовании код.

### Вы уже используете обобщения

Когда вы учитываете, что если вы использовали массивы, срезы или карты; вы _уже были потребителем обобщенного кода_.

```
var myApples []Apple
// You can't do this!
append(myApples, Orange{})
```

### Абстракция — не ругательство

Легко критиковать [AbstractSingletonProxyFactoryBean](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/aop/framework/AbstractSingletonProxyFactoryBean.html), но давайте не будем притворяться, что кодовая база без абстракций вовсе не плоха. Ваша задача — _объединять_ связанные концепции, когда это уместно, чтобы ваша система была легче для понимания и изменения; вместо того чтобы быть набором разрозненных функций и типов с отсутствием ясности.

### [Заставь это работать, сделай это правильно, сделай это быстро](https://wiki.c2.com/?MakeItWorkMakeItRightMakeItFast#:~:text=%22Make%20it%20work%2C%20make%20it,to%20DesignForPerformance%20ahead%20of%20time.)

Люди сталкиваются с проблемами при использовании обобщений, когда они абстрагируются слишком быстро, не имея достаточной информации для принятия хороших дизайнерских решений.

Цикл TDD (red, green, refactor) означает, что у вас есть больше указаний относительно того, какой код вам _действительно нужен_ для реализации вашего поведения, **вместо того чтобы придумывать абстракции заранее**; но вам все равно нужно быть осторожным.

Здесь нет жестких и быстрых правил, но сопротивляйтесь созданию обобщений, пока не увидите, что у вас есть полезное обобщение. Когда мы создавали различные реализации `Stack`, мы важно начали с _конкретного_ поведения, такого как `StackOfStrings` и `StackOfInts`, подкрепленного тестами. Из нашего _реального_ кода мы могли начать видеть реальные шаблоны, и, опираясь на наши тесты, мы могли исследовать рефакторинг в сторону более универсального решения.

Люди часто советуют обобщать только тогда, когда вы видите один и тот же код три раза, что кажется хорошим начальным правилом.

Распространенный путь, которым я шел в других языках программирования, был таким:

- Один цикл TDD для определения поведения
- Еще один цикл TDD для отработки других связанных сценариев

> Хм, эти вещи выглядят похожими — но небольшое дублирование лучше, чем привязка к плохой абстракции

- Переспать с этим
- Еще один цикл TDD

> Окей, я хотел бы попробовать обобщить эту вещь. Слава богу, я такой умный и красивый, потому что я использую TDD, поэтому я могу рефакторить, когда захочу, и этот процесс помог мне понять, какое поведение мне действительно нужно, прежде чем слишком много проектировать.

- Эта абстракция кажется хорошей! Тесты все еще проходят, и код стал проще
- Теперь я могу удалить ряд тестов, я уловил _суть_ поведения и убрал ненужные детали