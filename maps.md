# Отображения

**[Весь код для этой главы вы можете найти здесь](https://github.com/quii/learn-go-with-tests/tree/main/maps)**

В [массивах и срезах](arrays-and-slices.md) вы узнали, как хранить значения по порядку. Теперь мы рассмотрим способ хранения элементов по `key` (ключу) и быстрого их поиска.

Отображения (Maps) позволяют хранить элементы подобно словарю. Вы можете представлять `key` как слово, а `value` как определение. И какой лучший способ изучить отображения, чем создать свой собственный словарь?

Во-первых, если предположить, что у нас уже есть слова с их определениями в словаре, то при поиске слова оно должно возвращать его определение.

## Сначала напишите тест

В `dictionary_test.go`

```go
package main

import "testing"

func TestSearch(t *testing.T) {
	dictionary := map[string]string{"test": "this is just a test"}

	got := Search(dictionary, "test")
	want := "this is just a test"

	if got != want {
		t.Errorf("got %q want %q given, %q", got, want, "test")
	}
}
```

Объявление отображения (Map) чем-то похоже на объявление массива. За исключением того, что оно начинается с ключевого слова `map` и требует два типа. Первый — это тип ключа, который пишется внутри `[]`. Второй — это тип значения, который идёт сразу после `[]`.

Тип ключа является особенным. Он может быть только сравнимым типом, потому что без возможности определить, равны ли 2 ключа, у нас нет способа убедиться, что мы получаем правильное значение. Сравнимые типы подробно объяснены в [спецификации языка](https://golang.org/ref/spec#Comparison_operators).

Тип значения, с другой стороны, может быть любым типом, который вы хотите. Это может быть даже другое отображение (map).

Всё остальное в этом тесте должно быть вам знакомо.

## Попробуйте запустить тест

Запуск `go test` приведёт к ошибке компилятора: `./dictionary_test.go:8:9: undefined: Search`.

## Напишите минимальное количество кода, чтобы тест запустился и проверьте вывод

В `dictionary.go`

```go
package main

func Search(dictionary map[string]string, word string) string {
	return ""
}
```

Теперь ваш тест должен завершиться сбоем с *понятным сообщением об ошибке*:

`dictionary_test.go:12: got '' want 'this is just a test' given, 'test'`.

## Напишите достаточно кода, чтобы тест прошёл

```go
func Search(dictionary map[string]string, word string) string {
	return dictionary[word]
}
```

Получение значения из отображения (Map) такое же, как получение значения из массива: `map[key]`.

## Рефакторинг

```go
func TestSearch(t *testing.T) {
	dictionary := map[string]string{"test": "this is just a test"}

	got := Search(dictionary, "test")
	want := "this is just a test"

	assertStrings(t, got, want)
}

func assertStrings(t testing.TB, got, want string) {
	t.Helper()

	if got != want {
		t.Errorf("got %q want %q", got, want)
	}
}
```

Я решил создать вспомогательную функцию `assertStrings`, чтобы сделать реализацию более общей.

### Использование пользовательского типа

Мы можем улучшить использование нашего словаря, создав новый тип на основе `map` и сделав `Search` методом.

В `dictionary_test.go`:

```go
func TestSearch(t *testing.T) {
	dictionary := Dictionary{"test": "this is just a test"}

	got := dictionary.Search("test")
	want := "this is just a test"

	assertStrings(t, got, want)
}
```

Мы начали использовать тип `Dictionary`, который ещё не определили. Затем вызвали `Search` для экземпляра `Dictionary`.

Нам не нужно было изменять `assertStrings`.

В `dictionary.go`:

```go
type Dictionary map[string]string

func (d Dictionary) Search(word string) string {
	return d[word]
}
```

Здесь мы создали тип `Dictionary`, который действует как тонкая обёртка вокруг `map`. После определения пользовательского типа мы можем создать метод `Search`.

## Сначала напишите тест

Базовый поиск было очень легко реализовать, но что произойдёт, если мы введём слово, которого нет в нашем словаре?

На самом деле мы ничего не получаем в ответ. Это хорошо, потому что программа может продолжать работать, но есть и лучший подход. Функция может сообщить, что слова нет в словаре. Таким образом, пользователь не остаётся в неведении, не существует ли слова или просто нет его определения (это может показаться не очень полезным для словаря. Однако это сценарий, который может быть ключевым в других случаях использования).

```go
func TestSearch(t *testing.T) {
	dictionary := Dictionary{"test": "this is just a test"}

	t.Run("known word", func(t *testing.T) {
		got, _ := dictionary.Search("test")
		want := "this is just a test"

		assertStrings(t, got, want)
	})

	t.Run("unknown word", func(t *testing.T) {
		_, err := dictionary.Search("unknown")
		want := "could not find the word you were looking for"

		if err == nil {
			t.Fatal("expected to get an error.")
		}

		assertStrings(t, err.Error(), want)
	})
}
```

Способ обработки этого сценария в Go — это возврат второго аргумента, который является типом `Error`.

Обратите внимание, что, как мы видели в [разделе об указателях и ошибках](./pointers-and-errors.md), здесь, чтобы проверить сообщение об ошибке, мы сначала проверяем, что ошибка не `nil`, а затем используем метод `.Error()` для получения строки, которую затем можем передать в утверждение.

## Попробуйте запустить тест

Это не компилируется

```
./dictionary_test.go:18:10: assignment mismatch: 2 variables but 1 values
```

## Напишите минимальное количество кода, чтобы тест запустился и проверьте вывод

```go
func (d Dictionary) Search(word string) (string, error) {
	return d[word], nil
}
```

Теперь ваш тест должен завершиться сбоем с гораздо более понятным сообщением об ошибке.

`dictionary_test.go:22: expected to get an error.`

## Напишите достаточно кода, чтобы тест прошёл

```go
func (d Dictionary) Search(word string) (string, error) {
	definition, ok := d[word]
	if !ok {
		return "", errors.New("could not find the word you were looking for")
	}

	return definition, nil
}
```

Чтобы это прошло, мы используем интересное свойство поиска в отображении. Оно может возвращать 2 значения. Второе значение — это логическое (`boolean`) значение, которое указывает, был ли ключ успешно найден.

Это свойство позволяет нам различать слово, которое не существует, и слово, которое просто не имеет определения.

## Рефакторинг

```go
var ErrNotFound = errors.New("could not find the word you were looking for")

func (d Dictionary) Search(word string) (string, error) {
	definition, ok := d[word]
	if !ok {
		return "", ErrNotFound
	}

	return definition, nil
}
```

Мы можем избавиться от "магической" ошибки в нашей функции `Search`, выделив её в переменную. Это также позволит нам написать лучший тест.

```go
t.Run("unknown word", func(t *testing.T) {
	_, got := dictionary.Search("unknown")
	if got == nil {
		t.Fatal("expected to get an error.")
	}
	assertError(t, got, ErrNotFound)
})
```
```go
func assertError(t testing.TB, got, want error) {
	t.Helper()

	if got != want {
		t.Errorf("got error %q want %q", got, want)
	}
}
```

Создав новую вспомогательную функцию, мы смогли упростить наш тест и начать использовать переменную `ErrNotFound`, чтобы наш тест не завершался сбоем, если мы изменим текст ошибки в будущем.

## Сначала напишите тест

У нас есть отличный способ поиска по словарю. Однако у нас нет способа добавлять новые слова в наш словарь.

```go
func TestAdd(t *testing.T) {
	dictionary := Dictionary{}
	dictionary.Add("test", "this is just a test")

	want := "this is just a test"
	got, err := dictionary.Search("test")
	if err != nil {
		t.Fatal("should find added word:", err)
	}

	assertStrings(t, got, want)
}
```

В этом тесте мы используем нашу функцию `Search`, чтобы немного упростить проверку словаря.

## Напишите минимальное количество кода, чтобы тест запустился и проверьте вывод

В `dictionary.go`

```go
func (d Dictionary) Add(word, definition string) {
}
```

Теперь ваш тест должен завершиться сбоем

```
dictionary_test.go:31: should find added word: could not find the word you were looking for
```

## Напишите достаточно кода, чтобы тест прошёл

```go
func (d Dictionary) Add(word, definition string) {
	d[word] = definition
}
```

Добавление в отображение также похоже на массив. Вам просто нужно указать ключ и присвоить ему значение.

### Указатели, копии и т.д.

Интересное свойство отображений заключается в том, что вы можете изменять их, не передавая адрес (например, `&myMap`).

Это может заставить их *чувствовать себя* как "ссылочный тип", [но, как описывает Дэйв Чейни](https://dave.cheney.net/2017/04/30/if-a-map-isnt-a-reference-variable-what-is-it), это не так.

> Значение отображения — это указатель на структуру `runtime.hmap`.

Таким образом, когда вы передаёте отображение в функцию/метод, вы действительно копируете его, но только часть-указатель, а не базовую структуру данных, которая содержит данные.

Ловушка с отображениями заключается в том, что они могут иметь значение `nil`. `nil`-отображение ведёт себя как пустое отображение при чтении, но попытки записи в `nil`-отображение вызовут панику во время выполнения (runtime panic). Вы можете прочитать больше об отображениях [здесь](https://blog.golang.org/go-maps-in-action).

Поэтому вы никогда не должны инициализировать `nil`-переменную отображения:

```go
var m map[string]string
```

Вместо этого вы можете инициализировать пустое отображение или использовать ключевое слово `make` для создания отображения:

```go
var dictionary = map[string]string{}

// OR

var dictionary = make(map[string]string)
```

Оба подхода создают пустое `hash map` и указывают `dictionary` на него. Это гарантирует, что вы никогда не получите панику во время выполнения.

## Рефакторинг

В нашей реализации не так много для рефакторинга, но тест можно немного упростить.

```go
func TestAdd(t *testing.T) {
	dictionary := Dictionary{}
	word := "test"
	definition := "this is just a test"

	dictionary.Add(word, definition)

	assertDefinition(t, dictionary, word, definition)
}

func assertDefinition(t testing.TB, dictionary Dictionary, word, definition string) {
	t.Helper()

	got, err := dictionary.Search(word)
	if err != nil {
		t.Fatal("should find added word:", err)
	}
	assertStrings(t, got, definition)
}
```

Мы создали переменные для `word` и `definition` и перенесли проверку определения в отдельную вспомогательную функцию.

Наша функция `Add` выглядит хорошо. За исключением того, что мы не учли, что произойдёт, когда значение, которое мы пытаемся `Add` (добавить), уже существует!

Отображение не выдаст ошибку, если значение уже существует. Вместо этого оно просто перезапишет значение новым предоставленным. Это может быть удобно на практике, но делает имя нашей функции менее точным. `Add` не должна изменять существующие значения. Она должна только добавлять новые слова в наш словарь.

## Сначала напишите тест

```go
func TestAdd(t *testing.T) {
	t.Run("new word", func(t *testing.T) {
		dictionary := Dictionary{}
		word := "test"
		definition := "this is just a test"

		err := dictionary.Add(word, definition)

		assertError(t, err, nil)
		assertDefinition(t, dictionary, word, definition)
	})

	t.Run("existing word", func(t *testing.T) {
		word := "test"
		definition := "this is just a test"
		dictionary := Dictionary{word: definition}
		err := dictionary.Add(word, "new test")

		assertError(t, err, ErrWordExists)
		assertDefinition(t, dictionary, word, definition)
	})
}
```

Для этого теста мы изменили `Add` так, чтобы она возвращала ошибку, которую мы проверяем по новой переменной ошибки `ErrWordExists`. Мы также изменили предыдущий тест, чтобы проверять на `nil`-ошибку.

## Попробуйте запустить тест

Компилятор выдаст ошибку, потому что мы не возвращаем значение для `Add`.

```
./dictionary_test.go:30:13: dictionary.Add(word, definition) used as value
./dictionary_test.go:41:13: dictionary.Add(word, "new test") used as value
```

## Напишите минимальное количество кода, чтобы тест запустился и проверьте вывод

В `dictionary.go`

```go
var (
	ErrNotFound   = errors.New("could not find the word you were looking for")
	ErrWordExists = errors.New("cannot add word because it already exists")
)

func (d Dictionary) Add(word, definition string) error {
	d[word] = definition
	return nil
}
```

Теперь мы получаем ещё две ошибки. Мы всё ещё изменяем значение и возвращаем `nil`-ошибку.

```
dictionary_test.go:43: got error '%!q(<nil>)' want 'cannot add word because it already exists'
dictionary_test.go:44: got 'new test' want 'this is just a test'
```

## Напишите достаточно кода, чтобы тест прошёл

```go
func (d Dictionary) Add(word, definition string) error {
	_, err := d.Search(word)

	switch err {
	case ErrNotFound:
		d[word] = definition
	case nil:
		return ErrWordExists
	default:
		return err
	}

	return nil
}
```

Здесь мы используем оператор `switch` для сопоставления с ошибкой. Такой `switch` обеспечивает дополнительную страховку, на случай если `Search` вернёт ошибку, отличную от `ErrNotFound`.

## Рефакторинг

У нас не так много для рефакторинга, но по мере роста использования ошибок мы можем внести несколько изменений.

```go
const (
	ErrNotFound   = DictionaryErr("could not find the word you were looking for")
	ErrWordExists = DictionaryErr("cannot add word because it already exists")
)

type DictionaryErr string

func (e DictionaryErr) Error() string {
	return string(e)
}
```

Мы сделали ошибки константами; это потребовало от нас создания собственного типа `DictionaryErr`, который реализует интерфейс `error`. Вы можете прочитать больше о деталях в [этой отличной статье Дэйва Чейни](https://dave.cheney.net/2016/04/07/constant-errors). Проще говоря, это делает ошибки более переиспользуемыми и неизменяемыми.

Далее давайте создадим функцию для `Update` (обновления) определения слова.

## Сначала напишите тест

```go
func TestUpdate(t *testing.T) {
	word := "test"
	definition := "this is just a test"
	dictionary := Dictionary{word: definition}
	newDefinition := "new definition"

	dictionary.Update(word, newDefinition)

	assertDefinition(t, dictionary, word, newDefinition)
}
```

`Update` очень тесно связана с `Add` и будет нашей следующей реализацией.

## Попробуйте запустить тест

```
./dictionary_test.go:53:2: dictionary.Update undefined (type Dictionary has no field or method Update)
```

## Напишите минимальное количество кода, чтобы тест запустился и проверьте вывод неудачного теста

Мы уже знаем, как бороться с подобной ошибкой. Нам нужно определить нашу функцию.

```go
func (d Dictionary) Update(word, definition string) {}
```

С этим на месте, мы можем увидеть, что нам нужно изменить определение слова.

```
dictionary_test.go:55: got 'this is just a test' want 'new definition'
```

## Напишите достаточно кода, чтобы тест прошёл

Мы уже видели, как это сделать, когда исправляли проблему с `Add`. Поэтому давайте реализуем что-то очень похожее на `Add`.

```go
func (d Dictionary) Update(word, definition string) {
	d[word] = definition
}
```

Нам не нужно проводить рефакторинг, так как это было простое изменение. Однако теперь у нас та же проблема, что и с `Add`. Если мы передадим новое слово, `Update` добавит его в словарь.

## Сначала напишите тест

```go
t.Run("existing word", func(t *testing.T) {
	word := "test"
	definition := "this is just a test"
	dictionary := Dictionary{word: definition}
	newDefinition := "new definition"

	err := dictionary.Update(word, newDefinition)

	assertError(t, err, nil)
	assertDefinition(t, dictionary, word, newDefinition)
})

t.Run("new word", func(t *testing.T) {
	word := "test"
	definition := "this is just a test"
	dictionary := Dictionary{}

	err := dictionary.Update(word, definition)

	assertError(t, err, ErrWordDoesNotExist)
})
```

Мы добавили ещё один тип ошибки для случая, когда слово не существует. Мы также изменили `Update`, чтобы она возвращала значение `error`.

## Попробуйте запустить тест

```
./dictionary_test.go:53:16: dictionary.Update(word, newDefinition) used as value
./dictionary_test.go:64:16: dictionary.Update(word, definition) used as value
./dictionary_test.go:66:23: undefined: ErrWordDoesNotExist
```

На этот раз мы получили 3 ошибки, но мы знаем, как с ними справиться.

## Напишите минимальное количество кода, чтобы тест запустился и проверьте вывод неудачного теста

```go
const (
	ErrNotFound         = DictionaryErr("could not find the word you were looking for")
	ErrWordExists       = DictionaryErr("cannot add word because it already exists")
	ErrWordDoesNotExist = DictionaryErr("cannot perform operation on word because it does not exist")
)

func (d Dictionary) Update(word, definition string) error {
	d[word] = definition
	return nil
}
```

Мы добавили наш собственный тип ошибки и возвращаем `nil`-ошибку.

С этими изменениями мы теперь получаем очень чёткую ошибку:

```
dictionary_test.go:66: got error '%!q(<nil>)' want 'cannot update word because it does not exist'
```

## Напишите достаточно кода, чтобы тест прошёл

```go
func (d Dictionary) Update(word, definition string) error {
	_, err := d.Search(word)

	switch err {
	case ErrNotFound:
		return ErrWordDoesNotExist
	case nil:
		d[word] = definition
	default:
		return err
	}

	return nil
}
```

Эта функция выглядит почти идентично `Add`, за исключением того, что мы поменяли местами обновление `dictionary` и возврат ошибки.

### Заметка об объявлении новой ошибки для Update

Мы могли бы повторно использовать `ErrNotFound` и не добавлять новую ошибку. Однако часто лучше иметь точную ошибку для случая, когда обновление не удалось.

Наличие специфических ошибок даёт вам больше информации о том, что пошло не так. Вот пример в веб-приложении:

> Вы можете перенаправить пользователя, когда встречается `ErrNotFound`, но отобразить сообщение об ошибке, когда встречается `ErrWordDoesNotExist`.

Далее давайте создадим функцию для `Delete` (удаления) слова из словаря.

## Сначала напишите тест

```go
func TestDelete(t *testing.T) {
	word := "test"
	dictionary := Dictionary{word: "test definition"}

	dictionary.Delete(word)

	_, err := dictionary.Search(word)
	assertError(t, err, ErrNotFound)
}
```

Наш тест создаёт `Dictionary` со словом, а затем проверяет, было ли слово удалено.

## Попробуйте запустить тест

Запуск `go test` даёт нам:

```
./dictionary_test.go:74:6: dictionary.Delete undefined (type Dictionary has no field or method Delete)
```

## Напишите минимальное количество кода, чтобы тест запустился и проверьте вывод неудачного теста

```go
func (d Dictionary) Delete(word string) {

}
```

После добавления этого, тест сообщает нам, что мы не удаляем слово.

```
dictionary_test.go:78: got error '%!q(<nil>)' want 'could not find the word you were looking for'
```

## Напишите достаточно кода, чтобы тест прошёл

```go
func (d Dictionary) Delete(word string) {
	delete(d, word)
}
```

Go имеет встроенную функцию `delete`, которая работает с отображениями. Она принимает два аргумента и ничего не возвращает. Первый аргумент — это отображение, а второй — ключ, который нужно удалить.

## Рефакторинг
Здесь не так много для рефакторинга, но мы можем реализовать ту же логику, что и в `Update`, для обработки случаев, когда слово не существует.

```go
func TestDelete(t *testing.T) {
	t.Run("existing word", func(t *testing.T) {
		word := "test"
		dictionary := Dictionary{word: "test definition"}

		err := dictionary.Delete(word)

		assertError(t, err, nil)

		_, err = dictionary.Search(word)

		assertError(t, err, ErrNotFound)
	})

	t.Run("non-existing word", func(t *testing.T) {
		word := "test"
		dictionary := Dictionary{}

		err := dictionary.Delete(word)

		assertError(t, err, ErrWordDoesNotExist)
	})
}
```

## Попробуйте запустить тест

Компилятор выдаст ошибку, потому что мы не возвращаем значение для `Delete`.

```
./dictionary_test.go:77:10: dictionary.Delete(word) (no value) used as value
./dictionary_test.go:90:10: dictionary.Delete(word) (no value) used as value
```

## Напишите достаточно кода, чтобы тест прошёл

```go
func (d Dictionary) Delete(word string) error {
	_, err := d.Search(word)

	switch err {
	case ErrNotFound:
		return ErrWordDoesNotExist
	case nil:
		delete(d, word)
	default:
		return err
	}

	return nil
}
```

Мы снова используем оператор `switch` для сопоставления с ошибкой, когда пытаемся удалить слово, которого не существует.

## Подведение итогов

В этом разделе мы рассмотрели многое. Мы создали полный CRUD API (Create, Read, Update и Delete) для нашего словаря. В процессе мы научились:

*   Создавать отображения
*   Искать элементы в отображениях
*   Добавлять новые элементы в отображения
*   Обновлять элементы в отображениях
*   Удалять элементы из отображения
*   Узнали больше об ошибках
    *   Как создавать ошибки, которые являются константами
    *   Написание обёрток для ошибок