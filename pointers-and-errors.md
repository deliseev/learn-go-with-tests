# Указатели и ошибки

[**Весь код для этой главы вы можете найти здесь**](https://github.com/quii/learn-go-with-tests/tree/main/pointers)

В предыдущем разделе мы изучили структуры, которые позволяют нам объединять ряд значений, связанных с определенной концепцией.

В какой-то момент вы можете захотеть использовать структуры для управления состоянием, предоставляя методы, позволяющие пользователям изменять состояние таким образом, чтобы вы могли его контролировать.

**Финтех любит Go** и, хммм, биткоины? Давайте покажем, какую потрясающую банковскую систему мы можем создать.

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

## Напишите минимальное количество кода, чтобы тест запустился, и проверьте вывод ошибочного теста

Компилятор не знает, что такое `Wallet`, поэтому давайте ему об этом сообщим.

```go
type Wallet struct{}
```

Теперь мы создали наш кошелек, попробуйте снова запустить тест

```
./wallet_test.go:9:8: wallet.Deposit undefined (type Wallet has no field or method Deposit)
./wallet_test.go:11:15: wallet.Balance undefined (type Wallet has no field or method Balance)
```

Нам нужно определить эти методы.

Помните, что нужно делать ровно столько, чтобы тесты запустились. Мы должны убедиться, что наш тест падает правильно с понятным сообщением об ошибке.

```go
func (w Wallet) Deposit(amount int) {

}

func (w Wallet) Balance() int {
	return 0
}
```

Если этот синтаксис вам незнаком, вернитесь и прочитайте раздел о структурах.

Теперь тесты должны компилироваться и запускаться

`wallet_test.go:15: got 0 want 10`

## Напишите достаточно кода, чтобы тест прошел

Нам понадобится какая-то переменная _balance_ в нашей структуре для хранения состояния

```go
type Wallet struct {
	balance int
}
```

В Go, если символ (переменные, типы, функции и т.д.) начинается со строчной буквы, то он является приватным _за пределами пакета, в котором он определен_.

В нашем случае мы хотим, чтобы наши методы могли манипулировать этим значением, но никто другой.

Помните, что мы можем получить доступ к внутреннему полю `balance` в структуре, используя переменную-получатель.

```go
func (w Wallet) Deposit(amount int) {
	w.balance += amount
}

func (w Wallet) Balance() int {
	return w.balance
}
```

Когда наша карьера в финтехе обеспечена, запустите набор тестов и насладитесь прошедшим тестом

`wallet_test.go:15: got 0 want 10`

### Что-то не совсем так

Ну, это сбивает с толку, наш код выглядит так, будто он должен работать. Мы добавляем новую сумму к нашему балансу, а затем метод `Balance` должен возвращать текущее состояние.

В Go, **когда вы вызываете функцию или метод, аргументы** _**копируются**_.

При вызове `func (w Wallet) Deposit(amount int)` `w` является копией того, от чего мы вызвали метод.

Не углубляясь в информатику, когда вы создаете значение — например, кошелек, оно хранится где-то в памяти. Вы можете узнать _адрес_ этой области памяти с помощью `&myVal`.

Поэкспериментируйте, добавив несколько выводов в ваш код

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

Заполнитель `%p` выводит адреса памяти в шестнадцатеричной нотации с префиксом `0x`, а символ экранирования `\n` выводит новую строку. Обратите внимание, что мы получаем указатель (адрес памяти) на что-либо, помещая символ `&` в начало символа.

Теперь перезапустите тест

```
address of balance in Deposit is 0xc420012268
address of balance in test is 0xc420012260
```

Вы можете видеть, что адреса двух балансов различаются. Таким образом, когда мы изменяем значение баланса внутри кода, мы работаем с копией того, что пришло из теста. Следовательно, баланс в тесте остается неизменным.

Мы можем исправить это с помощью _указателей_. [Указатели](https://gobyexample.com/pointers) позволяют нам _указывать_ на некоторые значения, а затем изменять их. Таким образом, вместо того, чтобы брать копию всего `Wallet`, мы берем указатель на этот `Wallet`, чтобы мы могли изменить исходные значения внутри него.

```go
func (w *Wallet) Deposit(amount int) {
	w.balance += amount
}

func (w *Wallet) Balance() int {
	return w.balance
}
```

Разница заключается в том, что тип получателя — `*Wallet`, а не `Wallet`, что можно прочитать как "указатель на `Wallet`".

Попробуйте перезапустить тесты, и они должны пройти.

Теперь вы можете задаться вопросом, почему они прошли? Мы не разыменовывали указатель в функции, как это:

```go
func (w *Wallet) Balance() int {
	return (*w).balance
}
```

и, казалось бы, обращались к объекту напрямую. На самом деле, приведенный выше код, использующий `(*w)`, абсолютно верен. Однако создатели Go посчитали такую нотацию громоздкой, поэтому язык позволяет нам писать `w.balance` без явного разыменовывания. Эти указатели на структуры даже имеют свое собственное название: _указатели на структуры_ (struct pointers), и они [автоматически разыменовываются](https://golang.org/ref/spec#Method_values).

Технически вам не нужно изменять `Balance`, чтобы использовать получатель-указатель, так как копирование баланса вполне приемлемо. Однако, по соглашению, вы должны сохранять типы получателей ваших методов одинаковыми для согласованности.

## Рефакторинг

Мы сказали, что делаем биткоин-кошелек, но до сих пор о биткоинах не упоминали. Мы использовали `int`, потому что это хороший тип для подсчета!

Кажется, создавать структуру для этого немного излишне. `int` хорош с точки зрения своей работы, но он не описателен.

Go позволяет создавать новые типы на основе существующих.

Синтаксис такой: `type MyName OriginalType`

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

Давайте реализуем [Stringer](https://golang.org/pkg/fmt/#Stringer) для `Bitcoin`

```go
type Stringer interface {
	String() string
}
```

Этот интерфейс определен в пакете `fmt` и позволяет вам определять, как ваш тип печатается при использовании со строкой форматирования `%s` в выводах.

```go
func (b Bitcoin) String() string {
	return fmt.Sprintf("%d BTC", b)
}
```

Как вы видите, синтаксис создания метода для объявления типа такой же, как и для структуры.

Здесь нам не хватило дисциплины: мы добавили метод, не написав для него тест. Это нормально, мы не всегда святые, но не должны это игнорировать. Запуск `go test -cover` показал бы нам, что `String` не покрыт, что является хорошим поводом вернуться и спросить, стоит ли тестировать ретроспективно. Мы не должны гнаться за 100% покрытием ради него самого, но в этом случае `String` имеет свою собственную логику (`fmt.Sprintf`), которую стоит закрепить, поэтому давайте добавим тест.

```go
t.Run("Bitcoin String", func(t *testing.T) {
	btc := Bitcoin(10)
	got := btc.String()
	want := "10 BTC"

	if got != want {
		t.Errorf("got %s want %s", got, want)
	}
})
```

Далее нам нужно обновить строки форматирования наших тестов, чтобы они использовали `String()`.

```go
if got != want {
	t.Errorf("got %s want %s", got, want)
}
```

Чтобы увидеть это в действии, намеренно сломайте тест, чтобы мы могли это увидеть

`wallet_test.go:18: got 10 BTC want 20 BTC`

Это делает более понятным то, что происходит в нашем тесте.

Следующее требование — это функция `Withdraw`.

## Сначала напишите тест

Почти противоположность `Deposit()`

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

## Напишите минимальное количество кода, чтобы тест запустился, и проверьте вывод ошибочного теста

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

В наших тестах есть некоторая дубликация, давайте ее устраним.

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

Что должно произойти, если вы попытаетесь `Withdraw` больше, чем осталось на счете? На данный момент наше требование состоит в том, чтобы предполагать отсутствие овердрафта.

Как мы сигнализируем о проблеме при использовании `Withdraw`?

В Go, если вы хотите указать на ошибку, идиоматично, чтобы ваша функция возвращала `err` для вызывающей стороны, чтобы проверить ее и принять меры.

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

Мы хотим, чтобы `Withdraw` возвращал ошибку _если_ вы пытаетесь снять больше, чем у вас есть, и баланс должен оставаться прежним.

Затем мы проверяем, вернулась ли ошибка, проваливая тест, если она `nil`.

`nil` синонимичен с `null` из других языков программирования. Ошибки могут быть `nil`, потому что возвращаемый тип `Withdraw` будет `error`, который является интерфейсом. Если вы видите функцию, которая принимает аргументы или возвращает значения, являющиеся интерфейсами, они могут быть `nil`.

Как и `null`, если вы попытаетесь получить доступ к значению, которое является `nil`, это вызовет **панику во время выполнения**. Это плохо! Вы должны убедиться, что вы проверяете наличие `nil`.

## Попробуйте запустить тест

`./wallet_test.go:31:25: wallet.Withdraw(Bitcoin(100)) used as value`

Формулировка, возможно, немного неясна, но наше предыдущее намерение с `Withdraw` состояло в том, чтобы просто вызвать его, он никогда не возвращал значение. Чтобы это скомпилировалось, нам нужно изменить его так, чтобы у него был возвращаемый тип.

## Напишите минимальное количество кода, чтобы тест запустился, и проверьте вывод ошибочного теста

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

Не забудьте импортировать `errors` в ваш код.

`errors.New` создает новую `error` с сообщением по вашему выбору.

## Рефакторинг

Давайте создадим быструю вспомогательную функцию для наших проверок ошибок, чтобы улучшить читаемость теста.

```go
assertError := func(t testing.TB, err error) {
	t.Helper()
	if err == nil {
		t.Error("wanted an error but didn't get one")
	}
}
```

И в нашем тесте

```go
t.Run("withdraw insufficient funds", func(t *testing.T) {
	startingBalance := Bitcoin(20)
	wallet := Wallet{startingBalance}
	err := wallet.Withdraw(Bitcoin(100))

	assertError(t, err)
	assertBalance(t, wallet, startingBalance)
})
```

Надеемся, что, возвращая ошибку "oh no", вы подумали, что мы _можем_ доработать это, потому что это сообщение кажется не очень полезным.

Предполагая, что ошибка в конечном итоге возвращается пользователю, давайте обновим наш тест, чтобы он проверял какое-либо сообщение об ошибке, а не просто наличие ошибки.

## Сначала напишите тест

Обновим нашу вспомогательную функцию для `string` для сравнения.

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

Как вы видите, ошибки могут быть преобразованы в строку с помощью метода `.Error()`, что мы делаем для сравнения ее с желаемой строкой. Мы также убеждаемся, что ошибка не является `nil`, чтобы избежать вызова `.Error()` для `nil`.

И затем обновим вызывающий код

```go
t.Run("withdraw insufficient funds", func(t *testing.T) {
	startingBalance := Bitcoin(20)
	wallet := Wallet{startingBalance}
	err := wallet.Withdraw(Bitcoin(100))

	assertError(t, err, "cannot withdraw, insufficient funds")
	assertBalance(t, wallet, startingBalance)
})
```

Мы ввели `t.Fatal`, который остановит тест, если будет вызван. Это потому, что мы не хотим делать больше утверждений о возвращенной ошибке, если ее нет. Без этого тест продолжился бы до следующего шага и запаниковал бы из-за нулевого указателя.

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

Было бы очень неприятно, если бы тест провалился, если бы кто-то захотел перефразировать ошибку, и это слишком много деталей для нашего теста. Нам не _очень_ важно, какова точная формулировка, просто при определенных условиях возвращается какое-то осмысленное сообщение об ошибке, связанное со снятием средств.

В Go ошибки — это значения, поэтому мы можем вынести их в переменную и иметь для них единый источник правды.

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

Ключевое слово `var` позволяет нам определять значения, глобальные для пакета.

Это само по себе является позитивным изменением, потому что теперь наша функция `Withdraw` выглядит очень понятно.

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
		wallet.Withdraw(Bitcoin(10))
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

И теперь за тестом также легче следить.

Я вынес вспомогательные функции из основной тестовой функции просто для того, чтобы, когда кто-то открывает файл, он мог сначала начать читать наши утверждения, а не какие-либо вспомогательные функции.

Еще одно полезное свойство тестов заключается в том, что они помогают нам понять _реальное_ использование нашего кода, чтобы мы могли сделать сочувственный код. Мы видим здесь, что разработчик может просто вызвать наш код и выполнить проверку равенства `ErrInsufficientFunds` и действовать соответствующим образом.

### Непроверенные ошибки

Хотя компилятор Go очень помогает, иногда все же можно что-то упустить, а обработка ошибок иногда может быть сложной.

Есть один сценарий, который мы не тестировали. Чтобы найти его, запустите следующую команду в терминале, чтобы установить `errcheck` — один из многих линтеров, доступных для Go.

`go install github.com/kisielk/errcheck@latest`

Затем, находясь в каталоге с вашим кодом, запустите `errcheck .`

Вы должны получить что-то вроде

`wallet_test.go:17:18: wallet.Withdraw(Bitcoin(10))`

Это говорит нам о том, что мы не проверили ошибку, возвращаемую в этой строке кода. Эта строка кода на моем компьютере соответствует нашему обычному сценарию снятия средств, потому что мы не проверили, что если `Withdraw` выполнен успешно, то ошибка _не_ возвращается.

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

## Добавление контекста с помощью оборачивания ошибок

Сравнение `err` с `ErrInsufficientFunds` хорошо работает здесь, потому что `Withdraw` — единственное, что может его создать. Но реальные программы имеют слои — `Wallet` может использоваться `Bank`, который используется HTTP-обработчиком, и так далее. Если каждый слой просто возвращает полученную ошибку без изменений, все, что видит вызывающий код на несколько слоев выше, это `insufficient funds`, без понятия, какой счет или какая операция на самом деле не удалась.

Предположим, у нас есть функция, которая обрабатывает снятие средств для именованного счета:

```go
func ProcessWithdrawal(wallet *Wallet, accountID string, amount Bitcoin) error {
	if err := wallet.Withdraw(amount); err != nil {
		return fmt.Errorf("processing withdrawal for account %s: %w", accountID, err)
	}
	return nil
}
```

Глагол `%w` (введенный в Go 1.13) похож на `%v` тем, что он подставляет строку `err`, но он также делает то, чего не делает `%v`: он _оборачивает_ `err` внутри новой ошибки, которую возвращает `fmt.Errorf`, а не просто копирует ее сообщение в новую, несвязанную строку. Попробуйте:

```go
wallet := Wallet{Bitcoin(10)}
err := ProcessWithdrawal(&wallet, "acc-123", Bitcoin(100))
fmt.Println(err)
// processing withdrawal for account acc-123: cannot withdraw, insufficient funds
```

Мы сохранили полезный контекст ("какой счет, какая операция"), не теряя деталей того, что на самом деле пошло не так.

### Проверка обернутых ошибок

Теперь, когда `ProcessWithdrawal` возвращает _другое_ значение ошибки, нежели `ErrInsufficientFunds`, сравнение с `==` (или нашим помощником `assertError` выше) завершилось бы неудачей, хотя основная причина та же. Именно эту проблему решает [`errors.Is`](https://pkg.go.dev/errors#Is) — он проверяет цепочку обернутых ошибок, а не только самую внешнюю:

```go
if errors.Is(err, ErrInsufficientFunds) {
	// still true, even though err's message now also mentions the account
}
```

`errors.Is` работает путем многократного вызова [`errors.Unwrap`](https://pkg.go.dev/errors#Unwrap) на `err` (который знает, как получить обернутую ошибку обратно, потому что `fmt.Errorf` с `%w` производит значение с методом `Unwrap() error`), пока не найдет совпадение или не закончатся ошибки для разворачивания. Вы увидите, что `errors.Is` используется снова именно по этой причине во вспомогательной функции `assertError` в главе [Карты](maps.md) вместо `==` — это безопасное значение по умолчанию, которое также работает для ошибок, которые изначально не были обернуты.

Если вам нужно извлечь _типизированную_ ошибку (а не сравнивать со сигнальным значением, таким как `ErrInsufficientFunds`) из цепочки обернутых ошибок, для этого тоже есть эквивалентная функция: [`errors.As`](https://pkg.go.dev/errors#As). Глава [Типы ошибок](error-types.md) рассматривает это более подробно.

## В заключение

### Указатели

*   Go копирует значения при передаче их в функции/методы, поэтому, если вы пишете функцию, которой нужно изменять состояние, вам понадобится, чтобы она принимала указатель на то, что вы хотите изменить.
*   Тот факт, что Go делает копии значений, во многих случаях полезен, но иногда вам не захочется, чтобы ваша система делала копию чего-либо, и в этом случае вам нужно передать ссылку. Примеры включают ссылки на очень крупные структуры данных или вещи, для которых необходим только один экземпляр (например, пулы подключений к базам данных).

### nil

*   Указатели могут быть `nil`.
*   Когда функция возвращает указатель на что-либо, вам нужно убедиться, что вы проверяете, не является ли он `nil`, иначе вы можете вызвать исключение во время выполнения — компилятор здесь вам не поможет.
*   Полезно, когда вы хотите описать значение, которое может отсутствовать.

### Ошибки

*   Ошибки — это способ сигнализировать о сбое при вызове функции/метода.
*   Прислушиваясь к нашим тестам, мы пришли к выводу, что проверка строки в ошибке приведет к ненадежному тесту. Поэтому мы рефакторизировали нашу реализацию, чтобы использовать значимое значение, и это привело к более легкому тестированию кода, а также к выводу, что это будет проще для пользователей нашего API.
*   Это не конец истории с обработкой ошибок, вы можете делать более сложные вещи, но это всего лишь введение. В последующих разделах будут рассмотрены дополнительные стратегии.
*   [Не просто проверяйте ошибки, обрабатывайте их изящно](https://dave.cheney.net/2016/04/27/dont-just-check-errors-handle-them-gracefully)

### Создание новых типов на основе существующих

*   Полезно для добавления более специфичного для предметной области значения.
*   Может позволить вам реализовывать интерфейсы.

Указатели и ошибки являются важной частью написания кода на Go, с которой вам нужно освоиться. К счастью, компилятор _обычно_ помогает вам, если вы делаете что-то не так, просто не торопитесь и читайте сообщение об ошибке.