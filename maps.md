---
# Карты

**[Весь код для этой главы вы можете найти здесь](https://github.com/quii/learn-go-with-tests/tree/main/maps)**

В [массивах и срезах](arrays-and-slices.md) вы узнали, как хранить значения по порядку. Теперь мы рассмотрим способ хранения элементов по `ключу` и их быстрого поиска.

Карты позволяют хранить элементы подобно словарю. Вы можете представить `ключ` как слово, а `значение` как определение. И что может быть лучше для изучения Карт, чем создание собственного словаря?

Во-первых, предполагая, что у нас уже есть слова с их определениями в словаре, если мы ищем слово, оно должно возвращать его определение.

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

Объявление карты несколько похоже на объявление массива. За исключением того, что оно начинается с ключевого слова `map` и требует двух типов. Первый — это тип ключа, который пишется внутри `[]`. Второй — это тип значения, который идет сразу после `[]`.

Тип ключа особенный. Он может быть только сравнимым типом, потому что без возможности определить, равны ли два ключа, мы не можем гарантировать получение правильного значения. Сравнимые типы подробно объясняются в [спецификации языка](https://golang.org/ref/spec#Comparison_operators).

Тип значения, с другой стороны, может быть любым типом, какой вы захотите. Это может быть даже другая карта.

Все остальное в этом тесте должно быть знакомо.

## Попробуйте запустить тест

Запустив `go test`, компилятор выдаст ошибку `./dictionary_test.go:8:9: undefined: Search`.

## Напишите минимальный объем кода, чтобы тест запустился и проверьте вывод

В `dictionary.go`

```go
package main

func Search(dictionary map[string]string, word string) string {
	return ""
}
```

Ваш тест теперь должен завершиться сбоем с *понятным сообщением об ошибке*:

`dictionary_test.go:12: got '' want 'this is just a test' given, 'test'`.

## Напишите достаточно кода, чтобы тест прошел

```go
func Search(dictionary map[string]string, word string) string {
	return dictionary[word]
}
```

Получение значения из карты происходит так же, как получение значения из массива: `map[key]`.

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

Мы можем улучшить использование нашего словаря, создав новый тип на основе карты и сделав `Search` методом.

В `dictionary_test.go`:

```go
func TestSearch(t *testing.T) {
	dictionary := Dictionary{"test": "this is just a test"}

	got := dictionary.Search("test")
	want := "this is just a test"

	assertStrings(t, got, want)
}
```

Мы начали использовать тип `Dictionary`, который еще не определили. Затем вызвали `Search` на экземпляре `Dictionary`.

`assertStrings` не потребовал изменений.

В `dictionary.go`:

```go
type Dictionary map[string]string

func (d Dictionary) Search(word string) string {
	return d[word]
}
```

Здесь мы создали тип `Dictionary`, который действует как тонкая обертка над `map`. После определения пользовательского типа мы можем создать метод `Search`.

## Сначала напишите тест

Базовый поиск было очень легко реализовать, но что произойдет, если мы передадим слово, которого нет в нашем словаре?

На самом деле мы ничего не получаем в ответ. Это хорошо, потому что программа может продолжать работать, но есть лучший подход. Функция может сообщить, что слова нет в словаре. Таким образом, пользователь не останется в неведении, не существует ли слово или просто нет определения (это может показаться не очень полезным для словаря. Однако это сценарий, который может быть ключевым в других случаях использования).

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

В Go такой сценарий обрабатывается путем возврата второго аргумента типа `Error`.

Обратите внимание, что, как мы видели в разделе [указатели и ошибки](./pointers-and-errors.md), здесь, чтобы проверить сообщение об ошибке, мы сначала проверяем, что ошибка не `nil`, а затем используем метод `.Error()`, чтобы получить строку, которую затем можем передать в проверку.

## Попробуйте запустить тест

Это не компилируется

```
./dictionary_test.go:18:10: assignment mismatch: 2 variables but 1 values
```

## Напишите минимальный объем кода, чтобы тест запустился и проверьте вывод

```go
func (d Dictionary) Search(word string) (string, error) {
	return d[word], nil
}
```

Ваш тест теперь должен завершиться сбоем с гораздо более понятным сообщением об ошибке.

`dictionary_test.go:22: expected to get an error.`

## Напишите достаточно кода, чтобы тест прошел

```go
func (d Dictionary) Search(word string) (string, error) {
	definition, ok := d[word]
	if !ok {
		return "", errors.New("could not find the word you were looking for")
	}

	return definition, nil
}
```

Чтобы тест прошел, мы используем интересное свойство поиска по карте. Он может возвращать 2 значения. Второе значение — это логическое значение, которое указывает, был ли ключ успешно найден.

Это свойство позволяет нам различать слово, которого не существует, и слово, у которого просто нет определения.

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

Мы можем избавиться от "магической ошибки" в нашей функции `Search`, выделив ее в переменную. Это также позволит нам написать лучший тест.

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

	if !errors.Is(got, want) {
		t.Errorf("got error %q want %q", got, want)
	}
}
```

Создав новую вспомогательную функцию, мы смогли упростить наш тест и начать использовать нашу переменную `ErrNotFound`, чтобы наш тест не завершался сбоем, если мы изменим текст ошибки в будущем.

## Сначала напишите тест

У нас есть отличный способ искать в словаре. Однако у нас нет способа добавлять новые слова в наш словарь.

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

## Напишите минимальный объем кода, чтобы тест запустился и проверьте вывод

В `dictionary.go`

```go
func (d Dictionary) Add(word, definition string) {
}
```

Ваш тест теперь должен завершиться сбоем

```
dictionary_test.go:31: should find added word: could not find the word you were looking for
```

## Напишите достаточно кода, чтобы тест прошел

```go
func (d Dictionary) Add(word, definition string) {
	d[word] = definition
}
```

Добавление в карту также похоже на добавление в массив. Вам просто нужно указать ключ и присвоить ему значение.

### Указатели, копии и т. д.

Интересное свойство карт заключается в том, что вы можете изменять их, не передавая их по адресу (например, `&myMap`).

Это может создать ощущение, что они являются "ссылочным типом", [но, как описывает Дэйв Чейни](https://dave.cheney.net/2017/04/30/if-a-map-isnt-a-reference-variable-what-is-it), это не так.

> Значение карты — это указатель на структуру `runtime.hmap`.

Таким образом, когда вы передаете карту в функцию/метод, вы действительно копируете ее, но только часть указателя, а не базовую структуру данных, содержащую данные.

Подводный камень с картами заключается в том, что они могут быть `nil` значением. `nil`-карта ведет себя как пустая карта при чтении, но попытки записи в `nil`-карту вызовут панику во время выполнения. Вы можете узнать больше о картах [здесь](https://blog.golang.org/go-maps-in-action).

Поэтому вы никогда не должны инициализировать `nil`-переменную карты:

```go
var m map[string]string
```

Вместо этого вы можете инициализировать пустую карту или использовать ключевое слово `make` для ее создания:

```go
var dictionary = map[string]string{}

// ИЛИ

var dictionary = make(map[string]string)
```

Оба подхода создают пустую `хеш-карту` и указывают `dictionary` на нее. Это гарантирует, что вы никогда не получите паники во время выполнения.

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

Мы создали переменные для слова и определения и перенесли проверку определения в отдельную вспомогательную функцию.

Наш `Add` выглядит хорошо. За исключением того, что мы не учли, что произойдет, если значение, которое мы пытаемся добавить, уже существует!

Карта не выдаст ошибку, если значение уже существует. Вместо этого, она просто перезапишет значение новым. На практике это может быть удобно, но делает название нашей функции менее точным. `Add` не должна изменять существующие значения. Она должна только добавлять новые слова в наш словарь.

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

Для этого теста мы изменили `Add`, чтобы она возвращала ошибку, которую мы проверяем на соответствие новой переменной ошибки, `ErrWordExists`. Мы также изменили предыдущий тест, чтобы проверять на `nil` ошибку.

## Попробуйте запустить тест

Компилятор выдаст ошибку, потому что мы не возвращаем значение для `Add`.

```
./dictionary_test.go:30:13: dictionary.Add(word, definition) used as value
./dictionary_test.go:41:13: dictionary.Add(word, "new test") used as value
```

## Напишите минимальный объем кода, чтобы тест запустился и проверьте вывод

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

Теперь мы получаем еще две ошибки. Мы по-прежнему изменяем значение и возвращаем `nil` ошибку.

```
dictionary_test.go:43: got error '%!q(<nil>)' want 'cannot add word because it already exists'
dictionary_test.go:44: got 'new test' want 'this is just a test'
```

## Напишите достаточно кода, чтобы тест прошел

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

Здесь мы используем оператор `switch` для сопоставления с ошибкой. Такой `switch` обеспечивает дополнительную страховку на случай, если `Search` вернет ошибку, отличную от `ErrNotFound`.

## Рефакторинг

Нам не так много нужно рефакторить, но по мере роста использования ошибок мы можем внести несколько изменений.

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

Мы сделали ошибки константами; это потребовало от нас создания собственного типа `DictionaryErr`, который реализует интерфейс `error`. Вы можете узнать больше о деталях в [этой отличной статье Дэйва Чейни](https://dave.cheney.net/2016/04/07/constant-errors). Проще говоря, это делает ошибки более пригодными для повторного использования и неизменяемыми.

Далее создадим функцию для `Update` (обновления) определения слова.

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

`Update` очень тесно связан с `Add` и будет нашей следующей реализацией.

## Попробуйте запустить тест

```
./dictionary_test.go:53:2: dictionary.Update undefined (type Dictionary has no field or method Update)
```

## Напишите минимальный объем кода, чтобы тест запустился и проверьте вывод провалившегося теста

Мы уже знаем, как справляться с такой ошибкой. Нам нужно определить нашу функцию.

```go
func (d Dictionary) Update(word, definition string) {}
```

С этим на месте мы видим, что нам нужно изменить определение слова.

```
dictionary_test.go:55: got 'this is just a test' want 'new definition'
```

## Напишите достаточно кода, чтобы тест прошел

Мы уже видели, как это сделать, когда исправляли проблему с `Add`. Поэтому давайте реализуем нечто очень похожее на `Add`.

```go
func (d Dictionary) Update(word, definition string) {
	d[word] = definition
}
```

Здесь не требуется рефакторинг, поскольку это было простое изменение. Однако теперь у нас та же проблема, что и с `Add`. Если мы передадим новое слово, `Update` добавит его в словарь.

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

Мы добавили еще один тип ошибки для случая, когда слова не существует. Мы также изменили `Update`, чтобы она возвращала значение `error`.

## Попробуйте запустить тест

```
./dictionary_test.go:53:16: dictionary.Update(word, newDefinition) used as value
./dictionary_test.go:64:16: dictionary.Update(word, definition) used as value
./dictionary_test.go:66:23: undefined: ErrWordDoesNotExist
```

На этот раз мы получаем 3 ошибки, но мы знаем, как с ними справиться.

## Напишите минимальный объем кода, чтобы тест запустился и проверьте вывод провалившегося теста

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

Мы добавили наш собственный тип ошибки и возвращаем `nil` ошибку.

С этими изменениями мы теперь получаем очень понятную ошибку:

```
dictionary_test.go:66: got error '%!q(<nil>)' want 'cannot perform operation on word because it does not exist'
```

## Напишите достаточно кода, чтобы тест прошел

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

Эта функция выглядит почти идентично `Add`, за исключением того, что мы поменяли местами обновление `dictionary` и возвращение ошибки.

### Примечание по объявлению новой ошибки для Update

Мы могли бы повторно использовать `ErrNotFound` и не добавлять новую ошибку. Однако часто лучше иметь точную ошибку для случаев, когда обновление не удается.

Наличие специфических ошибок дает вам больше информации о том, что пошло не так. Вот пример в веб-приложении:

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

Наш тест создает `Dictionary` со словом, а затем проверяет, было ли слово удалено.

## Попробуйте запустить тест

Запустив `go test`, мы получаем:

```
./dictionary_test.go:74:6: dictionary.Delete undefined (type Dictionary has no field or method Delete)
```

## Напишите минимальный объем кода, чтобы тест запустился и проверьте вывод провалившегося теста

```go
func (d Dictionary) Delete(word string) {

}
```

После добавления этого тест сообщает нам, что мы не удаляем слово.

```
dictionary_test.go:78: got error '%!q(<nil>)' want 'could not find the word you were looking for'
```

## Напишите достаточно кода, чтобы тест прошел

```go
func (d Dictionary) Delete(word string) {
	delete(d, word)
}
```

Go имеет встроенную функцию `delete`, которая работает с картами. Она принимает два аргумента и ничего не возвращает. Первый аргумент — это карта, а второй — ключ, который нужно удалить.

## Рефакторинг
Рефакторить особо нечего, но мы можем реализовать ту же логику, что и в `Update`, для обработки случаев, когда слова не существует.

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

## Напишите достаточно кода, чтобы тест прошел

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

## Подводим итоги

В этом разделе мы рассмотрели многое. Мы создали полный CRUD API (Create, Read, Update и Delete — создание, чтение, обновление и удаление) для нашего словаря. В процессе мы научились:

*   Создавать карты
*   Искать элементы в картах
*   Добавлять новые элементы в карты
*   Обновлять элементы в картах
*   Удалять элементы из карты
*   Узнали больше об ошибках
    *   Как создавать константные ошибки
    *   Написание оберток для ошибок
---