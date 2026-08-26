# Введение в приемочное тестирование

На `$WORK` мы столкнулись с необходимостью "плавного завершения работы" (graceful shutdown) для наших сервисов. Плавное завершение работы гарантирует, что ваша система корректно завершит свою работу до того, как будет остановлена. Аналогией из реального мира было бы то, как человек пытается корректно завершить телефонный разговор, прежде чем перейти к следующей встрече, вместо того чтобы просто повесить трубку на полуслове.

Эта глава представит введение в плавное завершение работы в контексте HTTP-сервера, а также покажет, как писать "приемочные тесты", чтобы быть уверенным в поведении своего кода.

Прочитав эту главу, вы узнаете, как делиться пакетами с отличными тестами, сократить усилия по их поддержке и повысить уверенность в качестве своей работы.

## Достаточно информации о Kubernetes

Мы запускаем наше программное обеспечение на [Kubernetes](https://kubernetes.io/) (K8s). K8s завершает работу "подов" (на практике, нашего программного обеспечения) по различным причинам, и одной из распространенных является развертывание нового кода.

Мы устанавливаем высокие стандарты в отношении [метрик DORA](https://cloud.google.com/blog/products/devops-sre/using-the-four-keys-to-measure-your-devops-performance), поэтому мы работаем таким образом, чтобы развертывать небольшие, инкрементальные улучшения и функции в продакшн несколько раз в день.

Когда k8s хочет завершить работу пода, он инициирует ["жизненный цикл завершения"](https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-best-practices-terminating-with-grace), и частью этого является отправка сигнала SIGTERM нашему программному обеспечению. Таким образом k8s говорит нашему коду:

> Ты должен завершить свою работу, закончить всё, что делаешь, потому что после определенного "льготного периода" я отправлю `SIGKILL`, и для тебя наступит конец.

При получении `SIGKILL` любая работа, которую выполняла ваша программа, будет немедленно остановлена.

## If you do not have grace

Depending on the nature of your software, if you ignore `SIGTERM`, you can run into problems.

Our specific problem was with in-flight HTTP requests. When an automated test was exercising our API, if k8s decided to stop the pod, the server would die, the test would not get a response from the server, and the test will fail.

This would trigger an alert in our incidents channel which requires a dev to stop what they're doing and address the problem. These intermittent failures are an annoying distraction for our team.

These problems are not unique to our tests. If a user sends a request to your system and the process gets terminated mid-flight, they'll likely be greeted with a 5xx HTTP error, not the kind of user experience you want to deliver.

## When you have grace

What we want to do is listen for `SIGTERM`, and rather than instantly killing the server, we want to:

- Прекратить прослушивание новых запросов
- Позволить текущим запросам завершиться
- *Затем* завершить процесс

## How to have grace

Thankfully, Go already has a mechanism for gracefully shutting down a server with [net/http/Server.Shutdown](https://pkg.go.dev/net/http#Server.Shutdown).

> Shutdown gracefully shuts down the server without interrupting any active connections. Shutdown works by first closing all open listeners, then closing all idle connections, and then waiting indefinitely for connections to return to idle and then shut down. If the provided context expires before the shutdown is complete, Shutdown returns the context's error, otherwise it returns any error returned from closing the Server's underlying Listener(s).

To handle `SIGTERM` we can use [os/signal.Notify](https://pkg.go.dev/os/signal#Notify), which will send any incoming signals to a channel we provide.

By using these two features from the standard library, you can listen for `SIGTERM` and shutdown gracefully.

## Graceful shutdown package

To that end, I wrote [https://pkg.go.dev/github.com/quii/go-graceful-shutdown](https://pkg.go.dev/github.com/quii/go-graceful-shutdown). It provides a decorator function for a `*http.Server` to call its `Shutdown` method when a `SIGTERM` signal is detected

```go
func main() {
	var (
		ctx        = context.Background()
		httpServer = &http.Server{Addr: ":8080", Handler: http.HandlerFunc(acceptancetests.SlowHandler)}
		server     = gracefulshutdown.NewServer(httpServer)
	)

	if err := server.ListenAndServe(ctx); err != nil {
		// this will typically happen if our responses aren't written before the ctx deadline, not much can be done
		log.Fatalf("uh oh, didn't shutdown gracefully, some responses may have been lost %v", err)
	}

	// hopefully, you'll always see this instead
	log.Println("shutdown gracefully! all responses were sent")
}
```

The specifics around the code are not too important for this read, but it is worth having a quick look over the code before carrying on.

## Tests and feedback loops

When we wrote the `gracefulshutdown` package, we had unit tests to prove it behaves correctly which gave us the confidence to aggressively refactor. However, we still didn't feel "confident" that it **really** worked.

We added a `cmd` package and made a real program to use the package we were writing. We'd manually fire it up, fire off an HTTP request to it, and then send a `SIGTERM` to see what would happen.

**Инженер внутри вас должен чувствовать дискомфорт при ручном тестировании**. Это скучно, не масштабируется, неточно и расточительно. Если вы пишете пакет, которым собираетесь делиться, но при этом хотите сохранить его простым и дешевым в изменении, ручное тестирование не подойдет.

## Acceptance tests

If you’ve read the rest of this book, you will have mostly written "unit tests". Unit tests are a fantastic tool for enabling fearless refactoring, driving good modular design, preventing regressions, and facilitating fast feedback.

По своей природе они проверяют только небольшие части вашей системы. Обычно, одних модульных тестов *недостаточно* для эффективной стратегии тестирования. Помните, мы хотим, чтобы наши системы **всегда были готовы к развертыванию**. Мы не можем полагаться на ручное тестирование, поэтому нам нужен другой вид тестирования: **приемочные тесты**.

### What are they?

Приемочные тесты — это разновидность "тестирования черного ящика". Их иногда называют "функциональными тестами". Они должны проверять систему так, как это делал бы пользователь системы.

The term "black-box" refers to the idea that the test code has no access to the internals of the system, it can only use its public interface and make assertions on the behaviours it observes. This means they can only test the system as a whole.

This is an advantageous trait because it means the tests exercise the system the same as a user would, it can't use any special workarounds that could make a test pass, but not actually prove what you need to prove. This is similar to the principle of preferring your unit test files to live inside a separate test package, for example, `package mypkg_test` rather than `package mypkg`.

### Benefits of acceptance tests

- Когда они проходят, вы знаете, что вся ваша система ведет себя так, как вы хотите.
- Они более точные, быстрые и требуют меньше усилий, чем ручное тестирование.
- При правильном написании они служат точной, проверенной документацией вашей системы. Они не попадают в ловушку документации, которая расходится с реальным поведением системы.
- Никаких подделок! Всё по-настоящему.

### Potential drawbacks vs unit tests

- Их дорого писать.
- Они дольше выполняются.
- Они зависят от дизайна системы.
- Когда они падают, они обычно не дают вам первопричины, и их может быть трудно отлаживать.
- Они не дают обратной связи о внутреннем качестве вашей системы. Вы могли бы написать полный мусор и все равно добиться прохождения приемочного теста.
- Не все сценарии практично проверять из-за природы черного ящика.

For this reason, it is foolish to only rely on acceptance tests. They do not have many of the qualities unit tests have, and a system with a large number of acceptance tests will tend to suffer in terms of maintenance costs and poor lead time.

#### Lead time?

Время выполнения (Lead time) относится к тому, сколько времени проходит от слияния коммита в вашу основную ветку до его развертывания в продакшене. Это число может варьироваться от недель и даже месяцев для некоторых команд до считанных минут. Опять же, на `$WORK` мы ценим выводы DORA и хотим поддерживать наше время выполнения менее 10 минут.

Сбалансированный подход к тестированию необходим для надежной системы с отличным временем выполнения, и обычно это описывается в терминах [Пирамиды тестирования](https://martinfowler.com/articles/practical-test-pyramid.html).

## How to write basic acceptance tests

How does this relate to the original problem? We've just written a package here, and it is entirely unit-testable.

Как я уже упоминал, модульные тесты не давали нам достаточной уверенности. Мы хотим быть *действительно* уверены, что пакет работает при интеграции с реальной, запущенной программой. Мы должны быть в состоянии автоматизировать ручные проверки, которые мы проводили.

Let's take a look at the test program:

```go
func main() {
	var (
		ctx        = context.Background()
		httpServer = &http.Server{Addr: ":8080", Handler: http.HandlerFunc(acceptancetests.SlowHandler)}
		server     = gracefulshutdown.NewServer(httpServer)
	)

	if err := server.ListenAndServe(ctx); err != nil {
		// this will typically happen if our responses aren't written before the ctx deadline, not much can be done
		log.Fatalf("uh oh, didn't shutdown gracefully, some responses may have been lost %v", err)
	}

	// hopefully, you'll always see this instead
	log.Println("shutdown gracefully! all responses were sent")
}
```

You may have guessed that `SlowHandler` has a `time.Sleep` to delay responding, so I had time to `SIGTERM` and see what happens. The rest is fairly boilerplate:

- Создать `net/http/Server`;
- Обернуть его в библиотеку (см.: [Шаблон Декоратор](https://en.wikipedia.org/wiki/Decorator_pattern));
- Использовать обернутую версию для `ListenAndServe`.

### High-level steps for the acceptance test

- Собрать программу
- Запустить ее (и дождаться, пока она начнет прослушивать порт `8080`)
- Отправить HTTP-запрос на сервер
- Прежде чем сервер успеет отправить HTTP-ответ, отправить `SIGTERM`
- Проверить, получили ли мы ответ

### Building and running the program

```go
package acceptancetests

import (
	"fmt"
	"math/rand"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"time"
)

const (
	baseBinName = "temp-testbinary"
)

func LaunchTestProgram(port string) (cleanup func(), sendInterrupt func() error, err error) {
	binName, err := buildBinary()
	if err != nil {
		return nil, nil, err
	}

	sendInterrupt, kill, err := runServer(binName, port)

	cleanup = func() {
		if kill != nil {
			kill()
		}
		os.Remove(binName)
	}

	if err != nil {
		cleanup() // even though it's not listening correctly, the program could still be running
		return nil, nil, err
	}

	return cleanup, sendInterrupt, nil
}

func buildBinary() (string, error) {
	binName := randomString(10) + "-" + baseBinName

	build := exec.Command("go", "build", "-o", binName)

	if err := build.Run(); err != nil {
		return "", fmt.Errorf("cannot build tool %s: %s", binName, err)
	}
	return binName, nil
}

func runServer(binName string, port string) (sendInterrupt func() error, kill func(), err error) {
	dir, err := os.Getwd()
	if err != nil {
		return nil, nil, err
	}

	cmdPath := filepath.Join(dir, binName)

	cmd := exec.Command(cmdPath)

	if err := cmd.Start(); err != nil {
		return nil, nil, fmt.Errorf("cannot run temp converter: %s", err)
	}

	kill = func() {
		_ = cmd.Process.Kill()
	}

	sendInterrupt = func() error {
		return cmd.Process.Signal(syscall.SIGTERM)
	}

	err = waitForServerListening(port)

	return
}

func waitForServerListening(port string) error {
	for i := 0; i < 30; i++ {
		conn, _ := net.Dial("tcp", net.JoinHostPort("localhost", port))
		if conn != nil {
			conn.Close()
			return nil
		}
		time.Sleep(100 * time.Millisecond)
	}
	return fmt.Errorf("nothing seems to be listening on localhost:%s", port)
}

func randomString(n int) string {
	var letters = []rune("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

	s := make([]rune, n)
	for i := range s {
		s[i] = letters[rand.Intn(len(letters))]
	}
	return string(s)
}
```

`LaunchTestProgram` отвечает за:
- сборку программы
- запуск программы
- ожидание, пока она начнет прослушивать порт `8080`
- предоставление функции `cleanup` для завершения работы программы и ее удаления, чтобы гарантировать чистое состояние после завершения тестов
- предоставление функции `interrupt` для отправки программе `SIGTERM`, чтобы мы могли проверить поведение

Admittedly, this is not the nicest code in the world, but just focus on the exported function `LaunchTestProgram`, the un-exported functions it calls are uninteresting boilerplate.

Как уже обсуждалось, приемочное тестирование, как правило, сложнее настроить. Этот код значительно упрощает чтение *тестирующего* кода, и часто в случае приемочных тестов, как только вы написали церемониальный код, он готов, и вы можете о нем забыть.

### The acceptance test(s)

We wanted to have two acceptance tests for two programs, one with graceful shutdown and one without, so we, and the readers can see the difference in behaviour. With `LaunchTestProgram` to build and run the programs, it's quite simple to write acceptance tests for both, and we benefit from re-use with some helper functions.

Вот тест для сервера *с* плавным завершением работы, [тест без него вы найдете на GitHub](https://github.com/quii/go-graceful-shutdown/blob/main/acceptancetests/withoutgracefulshutdown/main_test.go)

```go
package main

import (
	"testing"
	"time"

	"github.com/quii/go-graceful-shutdown/acceptancetests"
	"github.com/quii/go-graceful-shutdown/assert"
)

const (
	port = "8080"
	url  = "<http://localhost:" + port
)

func TestGracefulShutdown(t *testing.T) {
	cleanup, sendInterrupt, err := acceptancetests.LaunchTestProgram(port)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(cleanup)

	// just check the server works before we shut things down
	assert.CanGet(t, url)

	// fire off a request, and before it has a chance to respond send SIGTERM.
	time.AfterFunc(50*time.Millisecond, func() {
		assert.NoError(t, sendInterrupt())
	})
	// Without graceful shutdown, this would fail
	assert.CanGet(t, url)

	// after interrupt, the server should be shutdown, and no more requests will work
	assert.CantGet(t, url)
}
```

With the setup encapsulated away, the tests are comprehensive, describe the behaviour, and are relatively easy to follow.

`assert.CanGet/CantGet` are helper functions I made to DRY up this common assertion for this suite.

```go
func CanGet(t testing.TB, url string) {
	errChan := make(chan error)

	go func() {
		res, err := http.Get(url)
		if err != nil {
			errChan <- err
			return
		}
		res.Body.Close()
		errChan <- nil
	}()

	select {
	case err := <-errChan:
		NoError(t, err)
	case <-time.After(3 * time.Second):
		t.Errorf("timed out waiting for request to %q", url)
	}
}
```

This will fire off a `GET` to `URL` on a goroutine, and if it responds without error before 3 seconds, then it will not fail. `CantGet` is omitted for brevity, [but you can view it on GitHub here](https://github.com/quii/go-graceful-shutdown/blob/main/assert/assert.go#L61).

Важно снова отметить, что Go предоставляет все необходимые инструменты для написания приемочных тестов "из коробки". Вам *не нужен* специальный фреймворк для создания приемочных тестов.

### Small investment with a big pay-off

Благодаря этим тестам читатели могут посмотреть на примеры программ и быть уверенными, что пример *действительно* работает, а значит, и в заявлениях пакета.

Importantly, as the author, we get **fast feedback** and **massive confidence** that the package works in a real-world setting.

```shell
go test -count=1 ./...
ok  	github.com/quii/go-graceful-shutdown	0.196s
?   	github.com/quii/go-graceful-shutdown/acceptancetests	[no test files]
ok  	github.com/quii/go-graceful-shutdown/acceptancetests/withgracefulshutdown	4.785s
ok  	github.com/quii/go-graceful-shutdown/acceptancetests/withoutgracefulshutdown	2.914s
?   	github.com/quii/go-graceful-shutdown/assert	[no test files]
```

## Wrapping up

In this blog post, we introduced acceptance tests into your testing tool belt. They are invaluable when you start to build real systems and are an important complement to your unit tests.

Природа того, *как* писать приемочные тесты, зависит от системы, которую вы создаете, но принципы остаются неизменными. Рассматривайте свою систему как "черный ящик". Если вы создаете веб-сайт, ваши тесты должны вести себя как пользователь, поэтому вам понадобится безголовый веб-браузер, такой как [Selenium](https://www.selenium.dev/), чтобы нажимать на ссылки, заполнять формы и т.д. Для RESTful API вы будете отправлять HTTP-запросы с помощью клиента.

### Taking it further for more complicated systems

Non-trivial systems don't tend to be single-process applications like the one we've discussed. Typically, you'll depend on other systems such as a database. For these scenarios, you'll need to automate a local environment to test with. Tools like [docker-compose](https://docs.docker.com/compose/) are useful for spinning up containers of the environment you need to run your system locally.

### The next chapter

In this post the acceptance test was written retrospectively. However, in [Growing Object-Oriented Software](http://www.growing-object-oriented-software.com) the authors show that we can use acceptance tests in a test-driven approach to act as a "north-star" to guide our efforts.

As systems get more complex, the costs of writing and maintaining acceptance tests can quickly spiral out of control. There are countless stories of development teams being hamstrung by expensive acceptance test suites.

В следующей главе будет рассказано об использовании приемочных тестов для руководства нашим дизайном, а также о принципах и методах управления затратами на приемочные тесты.

### Improving the quality of open-source

Если вы пишете пакеты, которыми собираетесь делиться, я бы посоветовал вам создавать простые примеры программ, демонстрирующие, что делает ваш пакет, и уделить время написанию легко воспринимаемых приемочных тестов, чтобы дать уверенность себе и потенциальным пользователям вашей работы.

Like [Testable Examples](https://go.dev/blog/examples), seeing this little extra effort in developer experience goes a long way toward building trust in your work, and will reduce your own maintenance costs.

## Recruitment plug for `$WORK`

Если вы хотите работать в среде с другими инженерами, решающими интересные проблемы, живете в Лондоне или Порту (или рядом) и вам понравилось содержание этой главы и книги — пожалуйста, [свяжитесь со мной в Twitter](https://twitter.com/quii), и, возможно, мы скоро сможем работать вместе!
