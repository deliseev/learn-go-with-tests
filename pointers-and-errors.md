# Указатели и ошибки

[**Весь код для этой главы вы найдете здесь**](https://github.com/quii/learn-go-with-tests/tree/main/pointers)

В предыдущем разделе мы изучили структуры, которые позволяют нам объединять несколько связанных значений вокруг одной концепции.

В какой-то момент вы можете захотеть использовать структуры для управления состоянием, предоставляя методы, позволяющие пользователям изменять это состояние контролируемым вами образом.

**Финтех любит Go** и эээ биткойны? Давайте покажем, какую удивительную банковскую систему мы можем создать.

Давайте создадим структуру `Wallet`, которая позволит нам вносить `Bitcoin`.

## Сначала напишите тест

```go
func TestWallet(t *testing.T) {

	wallet := Wallet{}

	wallet.Deposit(10)

	got := wallet.Balance()
	want := 10

	if got != want {
		t.Errorf("got %d want %d", got, want)
	}
}
```

В [предыдущем примере](structs-methods-and-interfaces.md) мы обращались к полям напрямую по их имени, однако в нашем _очень безопасном кошельке_ мы не хотим раскрывать наше внутреннее состояние остальному миру. Мы хотим контролировать доступ через методы.

## Попробуйте запустить тест

`./wallet_test.go:7:12: undefined: Wallet`

## Напишите минимальный объем кода, чтобы тест запустился, и проверьте вывод неудачного теста

Компилятор не знает, что такое `Wallet`, поэтому давайте ему об этом сообщим.

```go
type Wallet struct{}
```

Теперь, когда мы создали наш кошелек, попробуйте запустить тест снова.

```
./wallet_test.go:9:8: wallet.Deposit undefined (type Wallet has no field or method Deposit)
./wallet_test.go:11:15: wallet.Balance undefined (type Wallet has no field or method Balance)
```

Нам нужно определить эти методы.

Помните, что нужно делать ровно столько, сколько необходимо для запуска тестов. Мы должны убедиться, что наш тест падает корректно с ясным сообщением об ошибке.

```go
func (w Wallet) Deposit(amount int) {

}

func (w Wallet) Balance() int {
	return 0
}
```

Если этот синтаксис вам незнаком, вернитесь и прочитайте раздел о структурах.

Теперь тесты должны скомпилироваться и запуститься.

`wallet_test.go:15: got 0 want 10`

## Напишите достаточно кода, чтобы тест прошел

Нам понадобится какая-то переменная _balance_ в нашей структуре для хранения состояния.

```go
type Wallet struct {
	balance int
}
```

В Go, если символ (переменные, типы, функции и т.д.) начинается с символа в нижнем регистре, то он является приватным _за пределами пакета, в котором он определен_.

В нашем случае мы хотим, чтобы наши методы могли манипулировать этим значением, но никто другой.

Помните, что мы можем получить доступ к внутреннему полю `balance` в структуре, используя переменную "ресивера" (receiver).

```go
func (w Wallet) Deposit(amount int) {
	w.balance += amount
}

func (w Wallet) Balance() int {
	return w.balance
}
```

Обеспечив себе карьеру в финтехе, запустите набор тестов и насладитесь проходящим тестом.

`wallet_test.go:15: got 0 want 10`

### Что-то здесь не так

Это сбивает с толку, наш код, кажется, должен работать. Мы добавляем новую сумму к нашему балансу, а затем метод `Balance` должен возвращать его текущее состояние.

В Go, **когда вы вызываете функцию или метод, аргументы** _**копируются**_.

При вызове `func (w Wallet) Deposit(amount int)` переменная `w` является копией того, от чего мы вызвали метод.

Не вдаваясь в глубокие компьютерные науки, когда вы создаете значение — например, кошелек, оно хранится где-то в памяти. Вы можете узнать _адрес_ этой области памяти с помощью `&myVal`.

Поэкспериментируйте, добавив несколько операторов печати в свой код.

```go
func TestWallet(t *testing.T) {

	wallet := Wallet{}

	wallet.Deposit(10)

	got := wallet.Balance()

	fmt.Printf("address of balance in test is %p \n", &wallet.balance)

	want := 10

	if got != want {
		t.Errorf("got %d want %d", got, want)
	}
}
```

```go
func (w Wallet) Deposit(amount int) {
	fmt.Printf("address of balance in Deposit is %p \n", &w.balance)
	w.balance += amount
}
```

Заполнитель `%p` выводит адреса памяти в шестнадцатеричной нотации с ведущими `0x`, а escape-символ `\n` выводит новую строку. Обратите внимание, что мы получаем указатель (адрес памяти) на что-либо, помещая символ `&` в начало символа.

Теперь перезапустите тест.

```
address of balance in Deposit is 0xc420012268
address of balance in test is 0xc420012260
```

Вы видите, что адреса двух балансов различаются. Таким образом, когда мы изменяем значение `balance` внутри кода, мы работаем с копией того, что пришло из теста. Следовательно, `balance` в тесте остается неизменным.

Мы можем исправить это с помощью _указателей_. [Указатели](https://gobyexample.com/pointers) позволяют нам _указывать_ на некоторые значения, а затем изменять их. Таким образом, вместо того чтобы брать копию всего `Wallet`, мы берем указатель на этот `Wallet`, чтобы мы могли изменить исходные значения внутри него.

```go
func (w *Wallet) Deposit(amount int) {
	w.balance += amount
}

func (w *Wallet) Balance() int {
	return w.balance
}
```

Разница заключается в типе ресивера: `*Wallet`, а не `Wallet`, что можно прочитать как "указатель на кошелек".

Попробуйте перезапустить тесты, и они должны пройти.

Теперь вы можете задаться вопросом, почему они прошли? Мы не разыменовывали указатель в функции, например, так:

```go
func (w *Wallet) Balance() int {
	return (*w).balance
}
```

и, казалось бы, обращались к объекту напрямую. На самом деле, приведенный выше код, использующий `(*w)`, абсолютно корректен. Однако создатели Go посчитали эту нотацию громоздкой, поэтому язык позволяет нам писать `w.balance` без явного разыменования. Эти указатели на структуры даже имеют собственное имя: _структурные указатели_, и они [автоматически разыменовываются](https://golang.org/ref/spec#Method_values).

Технически, вам не нужно изменять `Balance`, чтобы использовать ресивер-указатель, так как копирование `balance` вполне допустимо. Однако, по соглашению, вы должны сохранять типы ресиверов методов одинаковыми для согласованности.

## Рефакторинг

Мы сказали, что делаем биткойн-кошелек, но пока что не упоминали о биткойнах. Мы использовали `int`, потому что это хороший тип для подсчета чего-либо!

Кажется, что создавать `структуру` для этого — это перебор. `int` вполне подходит с точки зрения его работы, но он не достаточно описателен.

Go позволяет создавать новые типы из существующих.

Синтаксис такой: `type MyName OriginalType`.

```go
type Bitcoin int

type Wallet struct {
	balance Bitcoin
}

func (w *Wallet) Deposit(amount Bitcoin) {
	w.balance += amount
}

func (w *Wallet) Balance() Bitcoin {
	return w.balance
}
```

```go
func TestWallet(t *testing.T) {

	wallet := Wallet{}

	wallet.Deposit(Bitcoin(10))

	got := wallet.Balance()

	want := Bitcoin(10)

	if got != want {
		t.Errorf("got %d want %d", got, want)
	}
}
```

Чтобы создать `Bitcoin`, вы просто используете синтаксис `Bitcoin(999)`.

Таким образом, мы создаем новый тип и можем объявлять на нем _методы_. Это может быть очень полезно, когда вы хотите добавить какую-либо специфичную для предметной области функциональность поверх существующих типов.

Давайте реализуем [Stringer](https://golang.org/pkg/fmt/#Stringer) для `Bitcoin`.

```go
type Stringer interface {
	String() string
}
```

Этот интерфейс определен в пакете `fmt` и позволяет вам определить, как ваш тип будет выводиться при использовании с форматной строкой `%s` в операторах печати.

```go
func (b Bitcoin) String() string {
	return fmt.Sprintf("%d BTC", b)
}
```

Как видите, синтаксис создания метода для объявления типа такой же, как и для структуры.

Далее нам нужно обновить форматные строки наших тестов, чтобы они использовали `String()` вместо этого.

```go
if got != want {
	t.Errorf("got %s want %s", got, want)
}
```

Чтобы увидеть это в действии, намеренно сломайте тест, чтобы мы могли это увидеть.

`wallet_test.go:18: got 10 BTC want 20 BTC`

Это делает более ясным то, что происходит в нашем тесте.

Следующее требование — это функция `Withdraw`.

## Сначала напишите тест

Почти противоположность `Deposit()`.

```go
func TestWallet(t *testing.T) {

	t.Run("deposit", func(t *testing.T) {
		wallet := Wallet{}

		wallet.Deposit(Bitcoin(10))

		got := wallet.Balance()

		want := Bitcoin(10)

		if got != want {
			t.Errorf("got %s want %s", got, want)
		}
	})

	t.Run("withdraw", func(t *testing.T) {
		wallet := Wallet{balance: Bitcoin(20)}

		wallet.Withdraw(Bitcoin(10))

		got := wallet.Balance()

		want := Bitcoin(10)

		if got != want {
			t.Errorf("got %s want %s", got, want)
		}
	})
}
```

## Попробуйте запустить тест

`./wallet_test.go:26:9: wallet.Withdraw undefined (type Wallet has no field or method Withdraw)`

## Напишите минимальный объем кода, чтобы тест запустился, и проверьте вывод неудачного теста

```go
func (w *Wallet) Withdraw(amount Bitcoin) {

}
```

`wallet_test.go:33: got 20 BTC want 10 BTC`

## Напишите достаточно кода, чтобы тест прошел

```go
func (w *Wallet) Withdraw(amount Bitcoin) {
	w.balance -= amount
}
```

## Рефакторинг

В наших тестах есть некоторое дублирование, давайте его устраним.

```go
func TestWallet(t *testing.T) {

	assertBalance := func(t testing.TB, wallet Wallet, want Bitcoin) {
		t.Helper()
		got := wallet.Balance()

		if got != want {
			t.Errorf("got %s want %s", got, want)
		}
	}

	t.Run("deposit", func(t *testing.T) {
		wallet := Wallet{}
		wallet.Deposit(Bitcoin(10))
		assertBalance(t, wallet, Bitcoin(10))
	})

	t.Run("withdraw", func(t *testing.T) {
		wallet := Wallet{balance: Bitcoin(20)}
		wallet.Withdraw(Bitcoin(10))
		assertBalance(t, wallet, Bitcoin(10))
	})

}
```

Что должно произойти, если вы попытаетесь `Withdraw` (снять) больше, чем осталось на счету? Пока что наше требование состоит в том, чтобы предполагать отсутствие овердрафта.

Как нам сообщить о проблеме при использовании `Withdraw`?

В Go, если вы хотите указать на ошибку, идиоматично, чтобы ваша функция возвращала `err` для проверки и дальнейших действий вызывающей стороной.

Давайте попробуем это в тесте.

## Сначала напишите тест

```go
t.Run("withdraw insufficient funds", func(t *testing.T) {
	startingBalance := Bitcoin(20)
	wallet := Wallet{startingBalance}
	err := wallet.Withdraw(Bitcoin(100))

	assertBalance(t, wallet, startingBalance)

	if err == nil {
		t.Error("wanted an error but didn't get one")
	}
})
```

Мы хотим, чтобы `Withdraw` возвращал ошибку, _если_ вы пытаетесь снять больше, чем у вас есть, и баланс должен оставаться прежним.

Затем мы проверяем, была ли возвращена ошибка, проваливая тест, если она `nil`.

`nil` — это синоним `null` из других языков программирования. Ошибки могут быть `nil`, потому что возвращаемый тип `Withdraw` будет `error`, который является интерфейсом. Если вы видите функцию, которая принимает аргументы или возвращает значения, являющиеся интерфейсами, они могут быть "обнуляемыми" (nillable).

Как и в случае с `null`, если вы попытаетесь получить доступ к значению, которое является `nil`, это вызовет **панику во время выполнения**. Это плохо! Вы должны убедиться, что вы проверяете значения на `nil`.

## Попробуйте запустить тест

`./wallet_test.go:31:25: wallet.Withdraw(Bitcoin(100)) used as value`

Формулировка, возможно, немного неясна, но наше предыдущее намерение с `Withdraw` состояло в том, чтобы просто вызвать его, и он никогда не должен был возвращать значение. Чтобы это скомпилировалось, нам нужно будет изменить его так, чтобы у него был возвращаемый тип.

## Напишите минимальный объем кода, чтобы тест запустился, и проверьте вывод неудачного теста

```go
func (w *Wallet) Withdraw(amount Bitcoin) error {
	w.balance -= amount
	return nil
}
```

Опять же, очень важно написать ровно столько кода, сколько необходимо для удовлетворения компилятора. Мы корректируем наш метод `Withdraw`, чтобы он возвращал `error`, и на данный момент мы должны что-то вернуть, поэтому давайте просто вернем `nil`.

## Напишите достаточно кода, чтобы тест прошел

```go
func (w *Wallet) Withdraw(amount Bitcoin) error {

	if amount > w.balance {
		return errors.New("oh no")
	}

	w.balance -= amount
	return nil
}
```

Не забудьте импортировать `errors` в свой код.

`errors.New` создает новую ошибку с выбранным вами сообщением.

## Рефакторинг

Давайте создадим быстрый вспомогательный инструмент для проверки ошибок, чтобы улучшить читаемость теста.

```go
assertError := func(t testing.TB, err error) {
	t.Helper()
	if err == nil {
		t.Error("wanted an error but didn't get one")
	}
}
```

И в нашем тесте:

```go
t.Run("withdraw insufficient funds", func(t *testing.T) {
	startingBalance := Bitcoin(20)
	wallet := Wallet{startingBalance}
	err := wallet.Withdraw(Bitcoin(100))

	assertError(t, err)
	assertBalance(t, wallet, startingBalance)
})
```

Надеемся, когда вы возвращали ошибку "oh no", вы думали, что мы _можем_ улучшить это, потому что это не кажется очень полезным для возврата.

Предполагая, что ошибка в конечном итоге будет возвращена пользователю, давайте обновим наш тест, чтобы он проверял какое-либо сообщение об ошибке, а не просто наличие ошибки.

## Сначала напишите тест

Обновите наш помощник для строки, с которой нужно сравнивать.

```go
assertError := func(t testing.TB, got error, want string) {
	t.Helper()

	if got == nil {
		t.Fatal("didn't get an error but wanted one")
	}

	if got.Error() != want {
		t.Errorf("got %q, want %q", got, want)
	}
}
```

Как видите, `Error`s могут быть преобразованы в строку с помощью метода `.Error()`, что мы и делаем для сравнения с нужной нам строкой. Мы также убеждаемся, что ошибка не `nil`, чтобы избежать вызова `.Error()` на `nil`.

А затем обновите вызывающую сторону.

```go
t.Run("withdraw insufficient funds", func(t *testing.T) {
	startingBalance := Bitcoin(20)
	wallet := Wallet{startingBalance}
	err := wallet.Withdraw(Bitcoin(100))

	assertError(t, err, "cannot withdraw, insufficient funds")
	assertBalance(t, wallet, startingBalance)
})
```

Мы ввели `t.Fatal`, который остановит тест, если он будет вызван. Это потому, что мы не хотим делать дальнейших утверждений относительно возвращаемой ошибки, если ее нет. Без этого тест продолжится до следующего шага и вызовет панику из-за нулевого указателя.

## Попробуйте запустить тест

`wallet_test.go:61: got err 'oh no' want 'cannot withdraw, insufficient funds'`

## Напишите достаточно кода, чтобы тест прошел

```go
func (w *Wallet) Withdraw(amount Bitcoin) error {

	if amount > w.balance {
		return errors.New("cannot withdraw, insufficient funds")
	}

	w.balance -= amount
	return nil
}
```

## Рефакторинг

У нас есть дублирование сообщения об ошибке как в тестовом коде, так и в коде `Withdraw`.

Будет очень неприятно, если тест провалится, если кто-то захочет перефразировать сообщение об ошибке, и это просто слишком много деталей для нашего теста. Нам не _очень_ важна точная формулировка, просто при определенном условии возвращается какое-то осмысленное сообщение об ошибке, связанное с выводом средств.

В Go ошибки — это значения, поэтому мы можем вынести их в переменную и иметь единый источник истины для нее.

```go
var ErrInsufficientFunds = errors.New("cannot withdraw, insufficient funds")

func (w *Wallet) Withdraw(amount Bitcoin) error {

	if amount > w.balance {
		return ErrInsufficientFunds
	}

	w.balance -= amount
	return nil
}
```

Ключевое слово `var` позволяет нам определять глобальные для пакета значения.

Это само по себе позитивное изменение, потому что теперь наша функция `Withdraw` выглядит очень понятно.

Далее мы можем рефакторить наш тестовый код, чтобы использовать это значение вместо конкретных строк.

```go
func TestWallet(t *testing.T) {

	t.Run("deposit", func(t *testing.T) {
		wallet := Wallet{}
		wallet.Deposit(Bitcoin(10))
		assertBalance(t, wallet, Bitcoin(10))
	})

	t.Run("withdraw with funds", func(t *testing.T) {
		wallet := Wallet{Bitcoin(20)}
		err := wallet.Withdraw(Bitcoin(10))

		assertError(t, err, ErrInsufficientFunds)
		assertBalance(t, wallet, Bitcoin(10))
	})

	t.Run("withdraw insufficient funds", func(t *testing.T) {
		wallet := Wallet{Bitcoin(20)}
		err := wallet.Withdraw(Bitcoin(100))

		assertError(t, err, ErrInsufficientFunds)
		assertBalance(t, wallet, Bitcoin(20))
	})
}

func assertBalance(t testing.TB, wallet Wallet, want Bitcoin) {
	t.Helper()
	got := wallet.Balance()

	if got != want {
		t.Errorf("got %q want %q", got, want)
	}
}

func assertError(t testing.TB, got, want error) {
	t.Helper()
	if got == nil {
		t.Fatal("didn't get an error but wanted one")
	}

	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}
```

И теперь за тестом стало легче следить.

Я переместил вспомогательные функции из основной тестовой функции просто для того, чтобы, когда кто-то открывает файл, он мог сначала начать читать наши утверждения, а не какие-то вспомогательные функции.

Еще одно полезное свойство тестов заключается в том, что они помогают нам понять _реальное_ использование нашего кода, чтобы мы могли создавать сочувствующий код. Мы видим, что разработчик может просто вызвать наш код и выполнить проверку равенства с `ErrInsufficientFunds` и действовать соответствующим образом.

### Непроверенные ошибки

Хотя компилятор Go вам сильно помогает, иногда есть вещи, которые вы всё ещё можете упустить, и обработка ошибок иногда может быть сложной.

Есть один сценарий, который мы не тестировали. Чтобы найти его, запустите следующее в терминале для установки `errcheck` — одного из многих доступных линтеров для Go.

`go install github.com/kisielk/errcheck@latest`

Затем в каталоге с вашим кодом запустите `errcheck .`

Вы должны получить что-то вроде:

`wallet_test.go:17:18: wallet.Withdraw(Bitcoin(10))`

Это говорит нам о том, что мы не проверили ошибку, возвращаемую на этой строке кода. Эта строка кода на моем компьютере соответствует нашему обычному сценарию вывода средств, потому что мы не проверили, что если `Withdraw` успешно, то ошибка _не_ возвращается.

Вот окончательный тестовый код, который учитывает это.

```go
func TestWallet(t *testing.T) {

	t.Run("deposit", func(t *testing.T) {
		wallet := Wallet{}
		wallet.Deposit(Bitcoin(10))

		assertBalance(t, wallet, Bitcoin(10))
	})

	t.Run("withdraw with funds", func(t *testing.T) {
		wallet := Wallet{Bitcoin(20)}
		err := wallet.Withdraw(Bitcoin(10))

		assertNoError(t, err)
		assertBalance(t, wallet, Bitcoin(10))
	})

	t.Run("withdraw insufficient funds", func(t *testing.T) {
		wallet := Wallet{Bitcoin(20)}
		err := wallet.Withdraw(Bitcoin(100))

		assertError(t, err, ErrInsufficientFunds)
		assertBalance(t, wallet, Bitcoin(20))
	})
}

func assertBalance(t testing.TB, wallet Wallet, want Bitcoin) {
	t.Helper()
	got := wallet.Balance()

	if got != want {
		t.Errorf("got %s want %s", got, want)
	}
}

func assertNoError(t testing.TB, got error) {
	t.Helper()
	if got != nil {
		t.Fatal("got an error but didn't want one")
	}
}

func assertError(t testing.TB, got error, want error) {
	t.Helper()
	if got == nil {
		t.Fatal("didn't get an error but wanted one")
	}

	if got != want {
		t.Errorf("got %s, want %s", got, want)
	}
}
```

## Завершение

### Указатели

*   Go копирует значения, когда вы передаете их функциям/методам, поэтому, если вы пишете функцию, которой нужно изменить состояние, вам потребуется, чтобы она принимала указатель на то, что вы хотите изменить.
*   Тот факт, что Go делает копию значений, часто бывает полезен, но иногда вы не захотите, чтобы ваша система делала копию чего-либо, и в этом случае вам нужно передать ссылку. Примеры включают ссылки на очень большие структуры данных или на вещи, где требуется только один экземпляр (например, пулы подключений к базе данных).

### nil

*   Указатели могут быть `nil`.
*   Когда функция возвращает указатель на что-либо, вам нужно убедиться, что вы проверили его на `nil`, иначе вы можете вызвать исключение времени выполнения (runtime exception) — компилятор здесь вам не поможет.
*   Полезно, когда вы хотите описать значение, которое может отсутствовать.

### Ошибки

*   Ошибки — это способ сигнализировать о неудаче при вызове функции/метода.
*   Прислушиваясь к нашим тестам, мы пришли к выводу, что проверка строки в ошибке приведет к нестабильному тесту. Поэтому мы переработали нашу реализацию, чтобы использовать значимое значение, и это привело к более легко тестируемому коду, и мы пришли к выводу, что это будет проще и для пользователей нашего API.
*   Это не конец истории с обработкой ошибок, вы можете делать более сложные вещи, но это всего лишь введение. В последующих разделах будут рассмотрены дополнительные стратегии.
*   [Не просто проверяйте ошибки, обрабатывайте их изящно](https://dave.cheney.net/2016/04/27/dont-just-check-errors-handle-them-gracefully)

### Создание новых типов из существующих

*   Полезно для добавления более специфичного для предметной области значения.
*   Может позволить вам реализовать интерфейсы.

Указатели и ошибки — это большая часть написания кода на Go, с которой вам нужно освоиться. К счастью, компилятор _обычно_ поможет вам, если вы сделаете что-то не так, просто не торопитесь и прочитайте сообщение об ошибке.