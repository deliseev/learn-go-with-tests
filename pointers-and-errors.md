# Указатели и ошибки

[**Весь код для этой главы вы можете найти здесь**](https://github.com/quii/learn-go-with-tests/tree/main/pointers)

В предыдущем разделе мы изучили структуры (structs), которые позволяют нам объединять несколько значений, связанных с одной концепцией.

В какой-то момент вы можете захотеть использовать структуры для управления состоянием, предоставляя методы, чтобы пользователи могли изменять состояние контролируемым вами способом.

**Финтех обожает Go**, и эээм, биткойны? Так что давайте покажем, какую удивительную банковскую систему мы можем создать.

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

В [предыдущем примере](structs-methods-and-interfaces.md) мы получали доступ к полям напрямую по их имени, однако в нашем _очень безопасном кошельке_ мы не хотим раскрывать наше внутреннее состояние остальному миру. Мы хотим контролировать доступ через методы.

## Попробуйте запустить тест

`./wallet_test.go:7:12: undefined: Wallet`

## Напишите минимальный объём кода, чтобы тест запустился, и проверьте вывод ошибочного теста

Компилятор не знает, что такое `Wallet`, поэтому давайте ему об этом сообщим.

```go
type Wallet struct{}
```

Теперь, когда мы создали наш кошелёк, попробуйте снова запустить тест

```
./wallet_test.go:9:8: wallet.Deposit undefined (type Wallet has no field or method Deposit)
./wallet_test.go:11:15: wallet.Balance undefined (type Wallet has no field or method Balance)
```

Нам нужно определить эти методы.

Помните, что нужно делать только то, что необходимо для запуска тестов. Мы должны убедиться, что наш тест корректно завершается сбоем с чётким сообщением об ошибке.

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

## Напишите достаточный объём кода, чтобы тест прошёл

Нам потребуется какая-то переменная _balance_ в нашей структуре для хранения состояния.

```go
type Wallet struct {
	balance int
}
```

В Go, если символ (переменные, типы, функции и т.д.) начинается с символа нижнего регистра, то он является приватным _за пределами пакета, в котором он определён_.

В нашем случае мы хотим, чтобы наши методы могли манипулировать этим значением, но никто другой.

Помните, что мы можем получать доступ к внутреннему полю `balance` в структуре, используя переменную-«получатель» (receiver).

```go
func (w Wallet) Deposit(amount int) {
	w.balance += amount
}

func (w Wallet) Balance() int {
	return w.balance
}
```

Обеспечив себе карьеру в финтехе, запустите набор тестов и насладитесь их успешным прохождением.

`wallet_test.go:15: got 0 want 10`

### Что-то тут не так

Что ж, это сбивает с толку, наш код выглядит так, будто он должен работать. Мы добавляем новую сумму к нашему `balance`, а затем метод `Balance` должен возвращать его текущее состояние.

В Go, **когда вы вызываете функцию или метод, аргументы** _**копируются**_.

При вызове `func (w Wallet) Deposit(amount int)` переменная `w` является копией того, из чего мы вызвали метод.

Не углубляясь в информатику, когда вы создаёте значение — например, кошелёк, оно хранится где-то в памяти. Вы можете узнать _адрес_ этого участка памяти с помощью `&myVal`.

Поэкспериментируйте, добавив несколько выводов (print) в ваш код:

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

Заполнитель `%p` выводит адреса памяти в шестнадцатеричной системе счисления с префиксом `0x`, а экранирующий символ `\n` выводит новую строку. Обратите внимание, что мы получаем указатель (адрес в памяти) на что-либо, помещая символ `&` в начало символа.

Теперь перезапустите тест

```
address of balance in Deposit is 0xc420012268
address of balance in test is 0xc420012260
```

Вы можете видеть, что адреса двух `balance` разные. Таким образом, когда мы изменяем значение `balance` внутри кода, мы работаем с копией того, что пришло из теста. Следовательно, значение `balance` в тесте остаётся неизменным.

Мы можем исправить это с помощью _указателей_. [Указатели](https://gobyexample.com/pointers) позволяют нам _указывать_ на некоторые значения и затем изменять их. Таким образом, вместо того чтобы брать копию всего `Wallet`, мы берём указатель на этот кошелёк, чтобы мы могли изменять исходные значения внутри него.

```go
func (w *Wallet) Deposit(amount int) {
	w.balance += amount
}

func (w *Wallet) Balance() int {
	return w.balance
}
```

Разница в том, что тип получателя — `*Wallet`, а не `Wallet`, что можно прочитать как «указатель на кошелёк».

Попробуйте снова запустить тесты, и они должны пройти.

Теперь вы можете задаться вопросом, почему они прошли? Мы не разыменовали указатель в функции, как показано ниже:

```go
func (w *Wallet) Balance() int {
	return (*w).balance
}
```

и, казалось бы, обращались к объекту напрямую. На самом деле, код выше с использованием `(*w)` абсолютно корректен. Однако создатели Go сочли эту нотацию громоздкой, поэтому язык позволяет нам писать `w.balance` без явного разыменования. Эти указатели на структуры даже имеют собственное имя: _указатели на структуры_ (struct pointers), и они [автоматически разыменовываются](https://golang.org/ref/spec#Method_values).

Технически вам не нужно менять `Balance` для использования получателя-указателя, так как создание копии баланса вполне допустимо. Однако, по соглашению, вы должны сохранять типы получателей ваших методов одинаковыми для обеспечения согласованности.

## Рефакторинг

Мы сказали, что создаём Биткойн-кошелёк, но до сих пор не упоминали их. Мы использовали `int`, потому что это хороший тип для подсчёта!

Создавать структуру для этого кажется немного избыточным. `int` вполне подходит с точки зрения своей работы, но он не является описательным.

Go позволяет создавать новые типы из существующих.

Синтаксис таков: `type MyName OriginalType`

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

Делая это, мы создаём новый тип и можем объявлять для него _методы_. Это может быть очень полезно, когда вы хотите добавить какую-либо предметно-ориентированную функциональность поверх существующих типов.

Давайте реализуем [Stringer](https://golang.org/pkg/fmt/#Stringer) для `Bitcoin`.

```go
type Stringer interface {
	String() string
}
```

Этот интерфейс определён в пакете `fmt` и позволяет определить, как ваш тип выводится при использовании с форматирующей строкой `%s` в функциях печати.

```go
func (b Bitcoin) String() string {
	return fmt.Sprintf("%d BTC", b)
}
```

Как видите, синтаксис создания метода для объявления типа такой же, как и для структуры.

Здесь нам не хватило дисциплины: мы добавили метод, не написав для него тест заранее. Это нормально, мы не всегда святые, но и не должны позволять этому сходить с рук. Запуск `go test -cover` показал бы нам, что `String` не покрыт тестами, что является хорошим поводом вернуться и спросить, стоит ли тестировать ретроспективно. Мы не должны гнаться за 100%-ным покрытием ради самого покрытия, но в данном случае `String` имеет свою собственную логику (`fmt.Sprintf`), которую стоит закрепить, поэтому давайте добавим тест.

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

Далее нам нужно обновить наши форматирующие строки в тестах, чтобы они использовали `String()`.

```go
if got != want {
	t.Errorf("got %s want %s", got, want)
}
```

Чтобы увидеть это в действии, намеренно сломайте тест, чтобы мы могли увидеть это:

`wallet_test.go:18: got 10 BTC want 20 BTC`

Это делает более понятным, что происходит в нашем тесте.

Следующее требование — функция `Withdraw`.

## Сначала напишите тест

По сути, противоположность `Deposit()`.

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

## Напишите минимальный объём кода, чтобы тест запустился, и проверьте вывод ошибочного теста

```go
func (w *Wallet) Withdraw(amount Bitcoin) {

}
```

`wallet_test.go:33: got 20 BTC want 10 BTC`

## Напишите достаточный объём кода, чтобы тест прошёл

```go
func (w *Wallet) Withdraw(amount Bitcoin) {
	w.balance -= amount
}
```

## Рефакторинг

В наших тестах есть некоторое дублирование, давайте вынесем это в рефакторинг.

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

Что должно произойти, если вы попытаетесь `Withdraw` (снять) больше, чем осталось на счёте? На данный момент наше требование состоит в том, чтобы предположить отсутствие овердрафта.

Как нам сигнализировать о проблеме при использовании `Withdraw`?

В Go, если вы хотите указать на ошибку, идиоматично, чтобы ваша функция возвращала `err`, чтобы вызывающий код мог проверить и отреагировать.

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

Мы хотим, чтобы `Withdraw` возвращал ошибку _если_ вы попытаетесь снять больше, чем у вас есть, и баланс должен оставаться прежним.

Затем мы проверяем, что ошибка вернулась, завершая тест сбоем, если она `nil`.

`nil` синонимичен `null` из других языков программирования. Ошибки могут быть `nil`, потому что возвращаемый тип `Withdraw` будет `error`, что является интерфейсом. Если вы видите функцию, которая принимает аргументы или возвращает значения, являющиеся интерфейсами, они могут быть `nil`'овыми (нулевыми).

Как и в случае с `null`, если вы попытаетесь получить доступ к значению, которое является `nil`, это вызовет **панику во время выполнения**. Это плохо! Вы должны убедиться, что вы проверяете на `nil`.

## Попробуйте запустить тест

`./wallet_test.go:31:25: wallet.Withdraw(Bitcoin(100)) used as value`

Формулировка, возможно, немного неясна, но наше предыдущее намерение с `Withdraw` состояло в том, чтобы просто вызвать его; он никогда не возвращает значение. Чтобы это скомпилировалось, нам нужно изменить его так, чтобы у него был возвращаемый тип.

## Напишите минимальный объём кода, чтобы тест запустился, и проверьте вывод ошибочного теста

```go
func (w *Wallet) Withdraw(amount Bitcoin) error {
	w.balance -= amount
	return nil
}
```

Опять же, очень важно писать ровно столько кода, сколько необходимо для удовлетворения компилятора. Мы исправляем наш метод `Withdraw`, чтобы он возвращал `error`, и на данный момент нам нужно вернуть _что-то_, поэтому давайте просто вернём `nil`.

## Напишите достаточный объём кода, чтобы тест прошёл

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

`errors.New` создаёт новую `error` с сообщением по вашему выбору.

## Рефакторинг

Давайте создадим быстрый вспомогательный метод для проверки ошибок, чтобы улучшить читаемость теста.

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

Надеемся, что, возвращая ошибку «oh no», вы подумали, что мы _могли бы_ доработать это, потому что это сообщение не кажется очень полезным.

Предполагая, что ошибка в конечном итоге возвращается пользователю, давайте обновим наш тест, чтобы он проверял определённое сообщение об ошибке, а не просто наличие ошибки.

## Сначала напишите тест

Обновим наш вспомогательный метод для сравнения со `string`.

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

Как вы видите, `Error`ы могут быть преобразованы в строку с помощью метода `.Error()`, что мы и делаем, чтобы сравнить её со строкой, которую мы ожидаем. Мы также убеждаемся, что ошибка не `nil`, чтобы не вызывать `.Error()` на `nil`.

А затем обновите вызывающий код

```go
t.Run("withdraw insufficient funds", func(t *testing.T) {
	startingBalance := Bitcoin(20)
	wallet := Wallet{startingBalance}
	err := wallet.Withdraw(Bitcoin(100))

	assertError(t, err, "cannot withdraw, insufficient funds")
	assertBalance(t, wallet, startingBalance)
})
```

Мы ввели `t.Fatal`, который остановит тест, если он будет вызван. Это потому, что мы не хотим делать больше утверждений по возвращаемой ошибке, если её нет. Без этого тест продолжился бы до следующего шага и вызвал панику из-за нулевого указателя.

## Попробуйте запустить тест

`wallet_test.go:61: got err 'oh no' want 'cannot withdraw, insufficient funds'`

## Напишите достаточный объём кода, чтобы тест прошёл

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

Будет очень раздражающе, если тест провалится, если кто-то захочет переформулировать ошибку, и это слишком много деталей для нашего теста. Нам _действительно_ не важна точная формулировка, важно лишь, что возвращается какая-то осмысленная ошибка, связанная со снятием средств, при определённом условии.

В Go ошибки являются значениями, поэтому мы можем вынести её в переменную и иметь единый источник истины для неё.

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

Это само по себе является позитивным изменением, потому что теперь наша функция `Withdraw` выглядит очень ясно.

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

И теперь тест также стало легче отслеживать.

Я переместил вспомогательные функции за пределы основной тестовой функции просто для того, чтобы, когда кто-то открывает файл, он мог начать чтение наших утверждений первыми, а не каких-то вспомогательных функций.

Ещё одно полезное свойство тестов заключается в том, что они помогают нам понять _реальное_ использование нашего кода, чтобы мы могли создавать более удобный для использования код. Здесь мы видим, что разработчик может просто вызвать наш код, выполнить проверку равенства с `ErrInsufficientFunds` и действовать соответствующим образом.

### Непроверенные ошибки

Хотя компилятор Go очень помогает, иногда бывают вещи, которые вы всё равно можете упустить, и обработка ошибок иногда может быть сложной.

Существует один сценарий, который мы не протестировали. Чтобы его найти, запустите в терминале следующую команду для установки `errcheck`, одного из многих линтеров, доступных для Go.

`go install github.com/kisielk/errcheck@latest`

Затем, в директории с вашим кодом, запустите `errcheck .`

Вы должны получить что-то вроде:

`wallet_test.go:17:18: wallet.Withdraw(Bitcoin(10))`

Это говорит нам о том, что мы не проверили возвращаемую ошибку в этой строке кода. Эта строка кода на моём компьютере соответствует нашему обычному сценарию снятия средств, потому что мы не проверили, что если `Withdraw` успешен, то ошибка _не_ возвращается.

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

Сравнение `err` с `ErrInsufficientFunds` отлично работает здесь, потому что `Withdraw` — единственное, что может её произвести. Но реальные программы имеют слои — `Wallet` может использоваться `Bank`, который используется HTTP-обработчиком, и так далее. Если каждый слой просто возвращает полученную ошибку без изменений, всё, что видит вызывающий код на несколько уровней выше, это `insufficient funds` (недостаточно средств), без понятия, какой именно счёт или какая операция на самом деле провалилась.

Допустим, у нас есть функция, которая обрабатывает снятие средств для именованного счёта:

```go
func ProcessWithdrawal(wallet *Wallet, accountID string, amount Bitcoin) error {
	if err := wallet.Withdraw(amount); err != nil {
		return fmt.Errorf("processing withdrawal for account %s: %w", accountID, err)
	}
	return nil
}
```

Глагол `%w` (введённый в Go 1.13) похож на `%v` тем, что он подставляет строку `err`, но он также делает то, чего не делает `%v`: он _оборачивает_ `err` в новую ошибку, которую возвращает `fmt.Errorf`, вместо того чтобы просто скопировать его сообщение в новую, несвязанную строку. Попробуйте:

```go
wallet := Wallet{Bitcoin(10)}
err := ProcessWithdrawal(&wallet, "acc-123", Bitcoin(100))
fmt.Println(err)
// processing withdrawal for account acc-123: cannot withdraw, insufficient funds
```

Мы сохранили полезный контекст («какой счёт, какая операция»), не теряя деталей того, что на самом деле пошло не так на более низком уровне.

### Проверка обёрнутых ошибок

Теперь, когда `ProcessWithdrawal` возвращает _другое_ значение ошибки, чем `ErrInsufficientFunds`, сравнение с `==` (или нашим вспомогательным методом `assertError` выше) привело бы к сбою, хотя основная причина та же. Именно эту проблему решает [`errors.Is`](https://pkg.go.dev/errors#Is) — она проверяет цепочку обёрнутых ошибок, а не только самую внешнюю:

```go
if errors.Is(err, ErrInsufficientFunds) {
	// still true, even though err's message now also mentions the account
}
```

`errors.Is` работает, многократно вызывая [`errors.Unwrap`](https://pkg.go.dev/errors#Unwrap) для `err` (который знает, как получить обёрнутую ошибку обратно, потому что `fmt.Errorf` с `%w` производит значение с методом `Unwrap() error`), пока не найдёт совпадение или не закончатся ошибки для развёртывания. Вы увидите `errors.Is`, используемый снова именно по этой причине во вспомогательном методе `assertError` в главе [Карты](maps.md), вместо `==` — это безопасное значение по умолчанию, которое также работает для ошибок, которые изначально не были обёрнуты.

Если вам нужно извлечь _типизированную_ ошибку (вместо того чтобы сравнивать с «сторожевым» (sentinel) значением, таким как `ErrInsufficientFunds`) из цепочки обёрнутых ошибок, для этого тоже есть эквивалентная функция: [`errors.As`](https://pkg.go.dev/errors#As). Глава [Типы ошибок](error-types.md) рассматривает это более подробно.

## Итоги

### Указатели

*   Go копирует значения, когда вы передаёте их в функции/методы, поэтому, если вы пишете функцию, которая должна изменять состояние, ей потребуется принимать указатель на то, что вы хотите изменить.
*   Тот факт, что Go делает копию значений, часто полезен, но иногда вы не захотите, чтобы ваша система создавала копию чего-либо, и в этом случае вам нужно будет передать ссылку. Примеры включают ссылки на очень большие структуры данных или вещи, где необходим только один экземпляр (например, пулы подключений к базам данных).

### `nil`

*   Указатели могут быть `nil`.
*   Когда функция возвращает указатель на что-либо, вам нужно убедиться, что вы проверили, является ли он `nil`, иначе вы можете вызвать исключение во время выполнения — компилятор здесь вам не поможет.
*   Полезно, когда вы хотите описать значение, которое может отсутствовать.

### Ошибки

*   Ошибки — это способ сигнализировать о сбое при вызове функции/метода.
*   Прислушиваясь к нашим тестам, мы пришли к выводу, что проверка строки в ошибке приведёт к ненадёжному тесту. Поэтому мы рефакторизировали нашу реализацию, чтобы использовать вместо этого осмысленное значение, и это привело к более простому в тестировании коду, и мы заключили, что это будет проще и для пользователей нашего API.
*   Это не конец истории с обработкой ошибок, вы можете делать более сложные вещи, но это всего лишь введение. В последующих разделах будут рассмотрены другие стратегии.
*   [Не просто проверяйте ошибки, обрабатывайте их изящно](https://dave.cheney.net/2016/04/27/dont-just-check-errors-handle-them-gracefully)

### Создание новых типов из существующих

*   Полезно для добавления более предметно-ориентированного смысла значениям.
*   Может позволить вам реализовать интерфейсы.

Указатели и ошибки — это большая часть написания кода на Go, с которой вам необходимо освоиться. К счастью, компилятор _обычно_ поможет вам, если вы сделаете что-то не так, просто не торопитесь и прочитайте ошибку.