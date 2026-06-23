# Типы ошибок

**[Весь код можно найти здесь](https://github.com/quii/learn-go-with-tests/tree/main/q-and-a/error-types)**

**Создание собственных типов для ошибок может быть элегантным способом привести код в порядок, сделать его проще в использовании и тестировании.**

Педро из Gopher Slack спрашивает:

> Если я создаю ошибку вроде `fmt.Errorf("%s must be foo, got %s", bar, baz)`, есть ли способ проверить равенство без сравнения строкового значения?

Давайте создадим функцию, чтобы изучить эту идею.

```go
// DumbGetter will get the string body of url if it gets a 200
func DumbGetter(url string) (string, error) {
	res, err := http.Get(url)

	if err != nil {
		return "", fmt.Errorf("problem fetching from %s, %v", url, err)
	}

	if res.StatusCode != http.StatusOK {
		return "", fmt.Errorf("did not get 200 from %s, got %d", url, res.StatusCode)
	}

	defer res.Body.Close()
	body, _ := io.ReadAll(res.Body) // ignoring err for brevity

	return string(body), nil
}
```

Нередко пишут функции, которые могут завершиться неудачей по разным причинам, и мы хотим убедиться, что каждый сценарий обрабатывается правильно.

Как говорит Педро, мы _могли бы_ написать тест для ошибки статуса следующим образом.

```go
t.Run("when you don't get a 200 you get a status error", func(t *testing.T) {

	svr := httptest.NewServer(http.HandlerFunc(func(res http.ResponseWriter, req *http.Request) {
		res.WriteHeader(http.StatusTeapot)
	}))
	defer svr.Close()

	_, err := DumbGetter(svr.URL)

	if err == nil {
		t.Fatal("expected an error")
	}

	want := fmt.Sprintf("did not get 200 from %s, got %d", svr.URL, http.StatusTeapot)
	got := err.Error()

	if got != want {
		t.Errorf(`got "%v", want "%v"`, got, want)
	}
})
```

Этот тест создает сервер, который всегда возвращает `StatusTeapot`, а затем мы используем его URL в качестве аргумента `DumbGetter`, чтобы убедиться, что он правильно обрабатывает ответы, отличные от `200`.

## Проблемы с этим способом тестирования

Эта книга старается подчеркнуть: _прислушивайтесь к своим тестам_, и этот тест _не кажется_ хорошим:

- Мы конструируем ту же строку, что и производственный код, для ее тестирования
- Его неудобно читать и писать
- Действительно ли точная строка сообщения об ошибке является тем, что _нас на самом деле волнует_?

Что это нам говорит? Эргономика нашего теста отразится на другом фрагменте кода, который будет пытаться использовать наш код.

Как пользователь нашего кода реагирует на конкретный тип ошибок, которые мы возвращаем? Лучшее, что они могут сделать, это посмотреть на строку ошибки, что чрезвычайно чревато ошибками и ужасно для написания.

## Что мы должны сделать

С TDD мы получаем преимущество, попадая в образ мышления:

> Как _я_ хотел бы использовать этот код?

Что мы могли бы сделать для `DumbGetter`, так это предоставить пользователям способ использовать систему типов для понимания того, какая ошибка произошла.

Что, если `DumbGetter` мог бы вернуть нам что-то вроде

```go
type BadStatusError struct {
	URL    string
	Status int
}
```

Вместо "магической" строки у нас есть реальные _данные_ для работы.

Давайте изменим наш существующий тест, чтобы отразить эту потребность.

```go
t.Run("when you don't get a 200 you get a status error", func(t *testing.T) {

	svr := httptest.NewServer(http.HandlerFunc(func(res http.ResponseWriter, req *http.Request) {
		res.WriteHeader(http.StatusTeapot)
	}))
	defer svr.Close()

	_, err := DumbGetter(svr.URL)

	if err == nil {
		t.Fatal("expected an error")
	}

	got, isStatusErr := err.(BadStatusError)

	if !isStatusErr {
		t.Fatalf("was not a BadStatusError, got %T", err)
	}

	want := BadStatusError{URL: svr.URL, Status: http.StatusTeapot}

	if got != want {
		t.Errorf("got %v, want %v", got, want)
	}
})
```

Нам придется заставить `BadStatusError` реализовать интерфейс error.

```go
func (b BadStatusError) Error() string {
	return fmt.Sprintf("did not get 200 from %s, got %d", b.URL, b.Status)
}
```

### Что делает тест?

Вместо того чтобы проверять точную строку ошибки, мы выполняем [утверждение типа](https://tour.golang.org/methods/15) для ошибки, чтобы определить, является ли она `BadStatusError`. Это яснее отражает наше желание относительно _типа_ ошибки. Предполагая, что утверждение проходит, мы можем затем проверить, правильны ли свойства ошибки.

Когда мы запускаем тест, он сообщает нам, что мы не вернули правильный тип ошибки.

```
--- FAIL: TestDumbGetter (0.00s)
    --- FAIL: TestDumbGetter/when_you_dont_get_a_200_you_get_a_status_error (0.00s)
    	error-types_test.go:56: was not a BadStatusError, got *errors.errorString
```

Давайте исправим `DumbGetter`, обновив наш код обработки ошибок для использования нашего типа.

```go
if res.StatusCode != http.StatusOK {
	return "", BadStatusError{URL: url, Status: res.StatusCode}
}
```

Это изменение имело некоторые _действительно положительные эффекты_:

- Наша функция `DumbGetter` стала проще, она больше не заботится о тонкостях строки ошибки, она просто создает `BadStatusError`.
- Наши тесты теперь отражают (и документируют) то, что _может_ сделать пользователь нашего кода, если он решит выполнить более сложную обработку ошибок, чем просто логирование. Просто выполните утверждение типа, и вы получите легкий доступ к свойствам ошибки.
- Это по-прежнему "просто" `error`, поэтому, если они захотят, они могут передать ее выше по стеку вызовов или записать в лог как любую другую `error`.

## Подведение итогов

Если вы обнаруживаете, что тестируете несколько условий ошибок, не попадайте в ловушку сравнения сообщений об ошибках.

Это приводит к нестабильным и трудночитаемым/труднозаписываемым тестам, и это отражает трудности, с которыми столкнутся пользователи вашего кода, если им также потребуется начать действовать по-разному в зависимости от типа произошедших ошибок.

Всегда убедитесь, что ваши тесты отражают, как _вы_ хотели бы использовать свой код, поэтому в этом отношении рассмотрите возможность создания типов ошибок для инкапсуляции ваших типов ошибок. Это упрощает обработку различных типов ошибок для пользователей вашего кода, а также делает написание кода обработки ошибок проще и понятнее.

## Дополнение

Начиная с Go 1.13, появились новые способы работы с ошибками в стандартной библиотеке, которые описаны в [блоге Go](https://blog.golang.org/go1.13-errors).

```go
t.Run("when you don't get a 200 you get a status error", func(t *testing.T) {

	svr := httptest.NewServer(http.HandlerFunc(func(res http.ResponseWriter, req *http.Request) {
		res.WriteHeader(http.StatusTeapot)
	}))
	defer svr.Close()

	_, err := DumbGetter(svr.URL)

	if err == nil {
		t.Fatal("expected an error")
	}

	var got BadStatusError
	isBadStatusError := errors.As(err, &got)
	want := BadStatusError{URL: svr.URL, Status: http.StatusTeapot}

	if !isBadStatusError {
		t.Fatalf("was not a BadStatusError, got %T", err)
	}

	if got != want {
		t.Errorf("got %v, want %v", got, want)
	}
})
```

В этом случае мы используем [`errors.As`](https://pkg.go.dev/errors#example-As), чтобы попытаться извлечь нашу ошибку в наш пользовательский тип. Он возвращает `bool`, чтобы обозначить успех, и извлекает ее в `got` для нас.
---