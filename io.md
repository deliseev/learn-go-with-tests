# Ввод-вывод и сортировка

**[Вы можете найти весь код для этой главы здесь](https://github.com/quii/learn-go-with-tests/tree/main/io)**

[В предыдущей главе](json.md) мы продолжили итерировать наше приложение, добавив новую конечную точку `/league`. Попутно мы узнали, как работать с JSON, встраиванием типов и маршрутизацией.

Наш product owner несколько расстроена тем, что программное обеспечение теряет очки при перезапуске сервера. Это происходит потому, что наша реализация хранилища находится в памяти. Ей также не нравится, что мы не интерпретировали конечную точку `/league` как возвращающую игроков, упорядоченных по количеству побед!

## Текущий код

```go
// server.go
package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

// PlayerStore stores score information about players
type PlayerStore interface {
	GetPlayerScore(name string) int
	RecordWin(name string)
	GetLeague() []Player
}

// Player stores a name with a number of wins
type Player struct {
	Name string
	Wins int
}

// PlayerServer is a HTTP interface for player information
type PlayerServer struct {
	store PlayerStore
	http.Handler
}

const jsonContentType = "application/json"

// NewPlayerServer creates a PlayerServer with routing configured
func NewPlayerServer(store PlayerStore) *PlayerServer {
	p := new(PlayerServer)

	p.store = store

	router := http.NewServeMux()
	router.Handle("/league", http.HandlerFunc(p.leagueHandler))
	router.Handle("/players/", http.HandlerFunc(p.playersHandler))

	p.Handler = router

	return p
}

func (p *PlayerServer) leagueHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("content-type", jsonContentType)
	json.NewEncoder(w).Encode(p.store.GetLeague())
}

func (p *PlayerServer) playersHandler(w http.ResponseWriter, r *http.Request) {
	player := strings.TrimPrefix(r.URL.Path, "/players/")

	switch r.Method {
	case http.MethodPost:
		p.processWin(w, player)
	case http.MethodGet:
		p.showScore(w, player)
	}
}

func (p *PlayerServer) showScore(w http.ResponseWriter, player string) {
	score := p.store.GetPlayerScore(player)

	if score == 0 {
		w.WriteHeader(http.StatusNotFound)
	}

	fmt.Fprint(w, score)
}

func (p *PlayerServer) processWin(w http.ResponseWriter, player string) {
	p.store.RecordWin(player)
	w.WriteHeader(http.StatusAccepted)
}
```

```go
// in_memory_player_store.go
package main

func NewInMemoryPlayerStore() *InMemoryPlayerStore {
	return &InMemoryPlayerStore{map[string]int{}}
}

type InMemoryPlayerStore struct {
	store map[string]int
}

func (i *InMemoryPlayerStore) GetLeague() []Player {
	var league []Player
	for name, wins := range i.store {
		league = append(league, Player{name, wins})
	}
	return league
}

func (i *InMemoryPlayerStore) RecordWin(name string) {
	i.store[name]++
}

func (i *InMemoryPlayerStore) GetPlayerScore(name string) int {
	return i.store[name]
}
```

```go
// main.go
package main

import (
	"log"
	"net/http"
)

func main() {
	server := NewPlayerServer(NewInMemoryPlayerStore())
	log.Fatal(http.ListenAndServe(":5000", server))
}
```

Вы можете найти соответствующие тесты по ссылке в начале главы.

## Хранение данных

Для этого мы могли бы использовать десятки баз данных, но мы выберем очень простой подход. Мы будем хранить данные для этого приложения в файле в формате JSON.

Это делает данные очень портативными и относительно простыми в реализации.

Это не будет особенно хорошо масштабироваться, но, учитывая, что это прототип, пока все будет в порядке. Если наши обстоятельства изменятся и этот подход перестанет быть подходящим, его будет легко заменить на что-то другое благодаря абстракции `PlayerStore`, которую мы использовали.

Мы сохраним `InMemoryPlayerStore` на данный момент, чтобы интеграционные тесты продолжали проходить, пока мы разрабатываем наше новое хранилище. Как только мы убедимся, что наша новая реализация достаточна для прохождения интеграционных тестов, мы заменим ее и затем удалим `InMemoryPlayerStore`.

## Сначала пишем тест

К настоящему моменту вы должны быть знакомы с интерфейсами стандартной библиотеки для чтения данных (`io.Reader`), записи данных (`io.Writer`) и тем, как мы можем использовать стандартную библиотеку для тестирования этих функций без использования реальных файлов.

Чтобы эта работа была завершена, нам нужно будет реализовать `PlayerStore`, поэтому мы напишем тесты для нашего хранилища, вызывая методы, которые нам нужно реализовать. Мы начнем с `GetLeague`.

```go
//file_system_store_test.go
func TestFileSystemStore(t *testing.T) {

	t.Run("league from a reader", func(t *testing.T) {
		database := strings.NewReader(`[
			{"Name": "Cleo", "Wins": 10},
			{"Name": "Chris", "Wins": 33}]`)

		store := FileSystemPlayerStore{database}

		got := store.GetLeague()

		want := []Player{
			{"Cleo", 10},
			{"Chris", 33},
		}

		assertLeague(t, got, want)
	})
}
```

Мы используем `strings.NewReader`, который вернет нам `Reader`, который `FileSystemPlayerStore` будет использовать для чтения данных. В `main` мы откроем файл, который также является `Reader`.

## Пробуем запустить тест

```
# github.com/quii/learn-go-with-tests/io/v1
./file_system_store_test.go:15:12: undefined: FileSystemPlayerStore
```

## Пишем минимальный объем кода, чтобы тест запустился, и проверяем вывод упавшего теста

Давайте определим `FileSystemPlayerStore` в новом файле

```go
//file_system_store.go
type FileSystemPlayerStore struct{}
```

Попробуем еще раз

```
# github.com/quii/learn-go-with-tests/io/v1
./file_system_store_test.go:15:28: too many values in struct initializer
./file_system_store_test.go:17:15: store.GetLeague undefined (type FileSystemPlayerStore has no field or method GetLeague)
```

Он жалуется, потому что мы передаем `Reader`, но не ожидаем его, и метод `GetLeague` еще не определен.

```go
//file_system_store.go
type FileSystemPlayerStore struct {
	database io.Reader
}

func (f *FileSystemPlayerStore) GetLeague() []Player {
	return nil
}
```

Еще одна попытка...

```
=== RUN   TestFileSystemStore//league_from_a_reader
    --- FAIL: TestFileSystemStore//league_from_a_reader (0.00s)
        file_system_store_test.go:24: got [] want [{Cleo 10} {Chris 33}]
```

## Пишем достаточно кода, чтобы тест прошел

Мы уже читали JSON из ридера раньше

```go
//file_system_store.go
func (f *FileSystemPlayerStore) GetLeague() []Player {
	var league []Player
	json.NewDecoder(f.database).Decode(&league)
	return league
}
```

Тест должен пройти.

## Рефакторинг

Мы _уже_ делали это раньше! Наш тестовый код для сервера должен был декодировать JSON из ответа.

Давайте попробуем сделать это более DRY, выделив в функцию.

Создайте новый файл `league.go` и поместите это внутрь.

```go
//league.go
func NewLeague(rdr io.Reader) ([]Player, error) {
	var league []Player
	err := json.NewDecoder(rdr).Decode(&league)
	if err != nil {
		err = fmt.Errorf("problem parsing league, %v", err)
	}

	return league, err
}
```

Вызовем это в нашей реализации и в нашей вспомогательной функции `getLeagueFromResponse` в `server_test.go`

```go
//file_system_store.go
func (f *FileSystemPlayerStore) GetLeague() []Player {
	league, _ := NewLeague(f.database)
	return league
}
```

У нас пока нет стратегии обработки ошибок парсинга, но давайте продолжим.

### Проблемы с позиционированием

В нашей реализации есть недостаток. Прежде всего, давайте вспомним, как определен `io.Reader`.

```go
type Reader interface {
	Read(p []byte) (n int, err error)
}
```

В случае с файлом, можно представить, как он читается байт за байтом до конца. Что произойдет, если вы попытаетесь `Read` во второй раз?

Добавьте следующее в конец нашего текущего теста.

```go
//file_system_store_test.go

// read again
got = store.GetLeague()
assertLeague(t, got, want)
```

Мы хотим, чтобы это прошло, но если вы запустите тест, этого не произойдет.

Проблема в том, что наш `Reader` достиг конца, и больше нечего читать. Нам нужен способ сказать ему вернуться к началу.

[ReadSeeker](https://golang.org/pkg/io/#ReadSeeker) — это еще один интерфейс в стандартной библиотеке, который может помочь.

```go
type ReadSeeker interface {
	Reader
	Seeker
}
```

Помните встраивание? Это интерфейс, состоящий из `Reader` и [`Seeker`](https://golang.org/pkg/io/#Seeker)

```go
type Seeker interface {
	Seek(offset int64, whence int) (int64, error)
}
```

Это звучит хорошо, можем ли мы изменить `FileSystemPlayerStore`, чтобы он принимал этот интерфейс?

```go
//file_system_store.go
type FileSystemPlayerStore struct {
	database io.ReadSeeker
}

func (f *FileSystemPlayerStore) GetLeague() []Player {
	f.database.Seek(0, io.SeekStart)
	league, _ := NewLeague(f.database)
	return league
}
```

Попробуйте запустить тест, теперь он проходит! К счастью для нас, `strings.NewReader`, который мы использовали в нашем тесте, также реализует `ReadSeeker`, поэтому нам не пришлось вносить никаких других изменений.

Далее мы реализуем `GetPlayerScore`.

## Сначала пишем тест

```go
//file_system_store_test.go
t.Run("get player score", func(t *testing.T) {
	database := strings.NewReader(`[
		{"Name": "Cleo", "Wins": 10},
		{"Name": "Chris", "Wins": 33}]`)

	store := FileSystemPlayerStore{database}

	got := store.GetPlayerScore("Chris")

	want := 33

	if got != want {
		t.Errorf("got %d want %d", got, want)
	}
})
```

## Пробуем запустить тест

```
./file_system_store_test.go:38:15: store.GetPlayerScore undefined (type FileSystemPlayerStore has no field or method GetPlayerScore)
```

## Пишем минимальный объем кода, чтобы тест запустился, и проверяем вывод упавшего теста

Нам нужно добавить метод к нашему новому типу, чтобы тест скомпилировался.

```go
//file_system_store.go
func (f *FileSystemPlayerStore) GetPlayerScore(name string) int {
	return 0
}
```

Теперь он компилируется, и тест падает

```
=== RUN   TestFileSystemStore/get_player_score
    --- FAIL: TestFileSystemStore//get_player_score (0.00s)
        file_system_store_test.go:43: got 0 want 33
```

## Пишем достаточно кода, чтобы тест прошел

Мы можем пройтись по лиге, чтобы найти игрока и вернуть его счет

```go
//file_system_store.go
func (f *FileSystemPlayerStore) GetPlayerScore(name string) int {

	var wins int

	for _, player := range f.GetLeague() {
		if player.Name == name {
			wins = player.Wins
			break
		}
	}

	return wins
}
```

## Рефакторинг

Вы видели десятки рефакторингов вспомогательных функций для тестов, так что я оставлю это вам, чтобы вы заставили его работать.

```go
//file_system_store_test.go
t.Run("get player score", func(t *testing.T) {
	database := strings.NewReader(`[
		{"Name": "Cleo", "Wins": 10},
		{"Name": "Chris", "Wins": 33}]`)

	store := FileSystemPlayerStore{database}

	got := store.GetPlayerScore("Chris")
	want := 33
	assertScoreEquals(t, got, want)
})
```

Наконец, нам нужно начать записывать очки с помощью `RecordWin`.

## Сначала пишем тест

Наш подход довольно недальновиден для операций записи. Мы не можем (легко) просто обновить одну "строку" JSON в файле. Нам придется сохранять _всю_ новую репрезентацию нашей базы данных при каждой записи.

Как мы записываем? Обычно мы используем `Writer`, но у нас уже есть `ReadSeeker`. Потенциально у нас могло бы быть две зависимости, но стандартная библиотека уже предлагает нам интерфейс `ReadWriteSeeker`, который позволяет нам делать все, что нам потребуется с файлом.

Давайте обновим наш тип

```go
//file_system_store.go
type FileSystemPlayerStore struct {
	database io.ReadWriteSeeker
}
```

Посмотрим, скомпилируется ли

```
./file_system_store_test.go:15:34: cannot use database (type *strings.Reader) as type io.ReadWriteSeeker in field value:
    *strings.Reader does not implement io.ReadWriteSeeker (missing Write method)
./file_system_store_test.go:36:34: cannot use database (type *strings.Reader) as type io.ReadWriteSeeker in field value:
    *strings.Reader does not implement io.ReadWriteSeeker (missing Write method)
```

Неудивительно, что `strings.Reader` не реализует `ReadWriteSeeker`, так что же нам делать?

У нас есть два варианта

- Создавать временный файл для каждого теста. `*os.File` реализует `ReadWriteSeeker`. Преимущество этого в том, что это становится больше интеграционным тестом, мы действительно читаем и записываем из файловой системы, что даст нам очень высокий уровень уверенности. Недостатки заключаются в том, что мы предпочитаем модульные тесты, потому что они быстрее и, как правило, проще. Нам также потребуется проделать больше работы по созданию временных файлов, а затем убедиться, что они удалены после теста.
- Мы могли бы использовать стороннюю библиотеку. [Mattetti](https://github.com/mattetti) написал библиотеку [filebuffer](https://github.com/mattetti/filebuffer), которая реализует необходимый нам интерфейс и не затрагивает файловую систему.

Я не думаю, что здесь есть однозначно неправильный ответ, но, выбрав использование сторонней библиотеки, мне пришлось бы объяснять управление зависимостями! Поэтому мы будем использовать файлы.

Перед добавлением нашего теста нам нужно заставить остальные тесты скомпилироваться, заменив `strings.Reader` на `os.File`.

Давайте создадим несколько вспомогательных функций, которые создадут временный файл с некоторыми данными внутри него и абстрагируют наши тесты на счет.

```go
//file_system_store_test.go
func createTempFile(t testing.TB, initialData string) (io.ReadWriteSeeker, func()) {
	t.Helper()

	tmpfile, err := os.CreateTemp("", "db")

	if err != nil {
		t.Fatalf("could not create temp file %v", err)
	}

	tmpfile.Write([]byte(initialData))

	removeFile := func() {
		tmpfile.Close()
		os.Remove(tmpfile.Name())
	}

	return tmpfile, removeFile
}

func assertScoreEquals(t testing.TB, got, want int) {
	t.Helper()
	if got != want {
		t.Errorf("got %d want %d", got, want)
	}
}
```

[CreateTemp](https://pkg.go.dev/os#CreateTemp) создает временный файл для нашего использования. Значение `"db"`, которое мы передали, — это префикс, добавляемый к случайному имени файла, который он создаст. Это сделано для того, чтобы избежать случайного совпадения с другими файлами.

Вы заметите, что мы возвращаем не только наш `ReadWriteSeeker` (файл), но и функцию. Нам нужно убедиться, что файл удален после завершения теста. Мы не хотим, чтобы детали файлов просачивались в тест, так как это чревато ошибками и неинтересно для читателя. Возвращая функцию `removeFile`, мы можем позаботиться о деталях в нашей вспомогательной функции, а вызывающей стороне нужно только выполнить `defer cleanDatabase()`.

```go
//file_system_store_test.go
func TestFileSystemStore(t *testing.T) {

	t.Run("league from a reader", func(t *testing.T) {
		database, cleanDatabase := createTempFile(t, `[
			{"Name": "Cleo", "Wins": 10},
			{"Name": "Chris", "Wins": 33}]`)
		defer cleanDatabase()

		store := FileSystemPlayerStore{database}

		got := store.GetLeague()

		want := []Player{
			{"Cleo", 10},
			{"Chris", 33},
		}

		assertLeague(t, got, want)

		// read again
		got = store.GetLeague()
		assertLeague(t, got, want)
	})

	t.Run("get player score", func(t *testing.T) {
		database, cleanDatabase := createTempFile(t, `[
			{"Name": "Cleo", "Wins": 10},
			{"Name": "Chris", "Wins": 33}]`)
		defer cleanDatabase()

		store := FileSystemPlayerStore{database}

		got := store.GetPlayerScore("Chris")
		want := 33
		assertScoreEquals(t, got, want)
	})
}
```

Запустите тесты, и они должны пройти! Было довольно много изменений, но теперь кажется, что определение нашего интерфейса завершено, и добавлять новые тесты будет очень легко.

Давайте рассмотрим первую итерацию записи победы для существующего игрока

```go
//file_system_store_test.go
t.Run("store wins for existing players", func(t *testing.T) {
	database, cleanDatabase := createTempFile(t, `[
		{"Name": "Cleo", "Wins": 10},
		{"Name": "Chris", "Wins": 33}]`)
	defer cleanDatabase()

	store := FileSystemPlayerStore{database}

	store.RecordWin("Chris")

	got := store.GetPlayerScore("Chris")
	want := 34
	assertScoreEquals(t, got, want)
})
```

## Пробуем запустить тест

`./file_system_store_test.go:67:8: store.RecordWin undefined (type FileSystemPlayerStore has no field or method RecordWin)`

## Пишем минимальный объем кода, чтобы тест запустился, и проверяем вывод упавшего теста

Добавляем новый метод

```go
//file_system_store.go
func (f *FileSystemPlayerStore) RecordWin(name string) {

}
```

```
=== RUN   TestFileSystemStore/store_wins_for_existing_players
    --- FAIL: TestFileSystemStore/store_wins_for_existing_players (0.00s)
        file_system_store_test.go:71: got 33 want 34
```

Наша реализация пуста, поэтому возвращается старый счет.

## Пишем достаточно кода, чтобы тест прошел

```go
//file_system_store.go
func (f *FileSystemPlayerStore) RecordWin(name string) {
	league := f.GetLeague()

	for i, player := range league {
		if player.Name == name {
			league[i].Wins++
		}
	}

	f.database.Seek(0, io.SeekStart)
	json.NewEncoder(f.database).Encode(league)
}
```

Вы можете спросить себя, почему я делаю `league[i].Wins++`, а не `player.Wins++`.

Когда вы используете `range` по срезу, вам возвращаются текущий индекс цикла (в нашем случае `i`) и _копия_ элемента по этому индексу. Изменение значения `Wins` у копии не окажет никакого влияния на срез `league`, по которому мы итерируемся. По этой причине нам нужно получить ссылку на фактическое значение, сделав `league[i]`, а затем изменить это значение.

Если вы запустите тесты, они должны пройти.

## Рефакторинг

В `GetPlayerScore` и `RecordWin` мы итерируемся по `[]Player`, чтобы найти игрока по имени.

Мы могли бы провести рефакторинг этого общего кода внутри `FileSystemStore`, но мне кажется, что это может быть полезный код, который мы можем поднять в новый тип. Работа с "Лигой" до сих пор всегда была со `[]Player`, но мы можем создать новый тип с именем `League`. Это будет легче понять другим разработчикам, и тогда мы сможем привязать к этому типу полезные методы для нашего использования.

Внутри `league.go` добавьте следующее

```go
//league.go
type League []Player

func (l League) Find(name string) *Player {
	for i, p := range l {
		if p.Name == name {
			return &l[i]
		}
	}
	return nil
}
```

Теперь, если у кого-то есть `League`, он может легко найти нужного игрока.

Измените наш интерфейс `PlayerStore`, чтобы он возвращал `League` вместо `[]Player`. Попробуйте повторно запустить тесты, вы получите проблему компиляции, потому что мы изменили интерфейс, но ее очень легко исправить; просто измените тип возвращаемого значения с `[]Player` на `League`.

Это позволяет нам упростить наши методы в `file_system_store`.

```go
//file_system_store.go
func (f *FileSystemPlayerStore) GetPlayerScore(name string) int {

	player := f.GetLeague().Find(name)

	if player != nil {
		return player.Wins
	}

	return 0
}

func (f *FileSystemPlayerStore) RecordWin(name string) {
	league := f.GetLeague()
	player := league.Find(name)

	if player != nil {
		player.Wins++
	}

	f.database.Seek(0, io.SeekStart)
	json.NewEncoder(f.database).Encode(league)
}
```

Это выглядит гораздо лучше, и мы видим, как можно найти другую полезную функциональность вокруг `League`, которую можно отрефакторить.

Теперь нам нужно обработать сценарий записи побед новых игроков.

## Сначала пишем тест

```go
//file_system_store_test.go
t.Run("store wins for new players", func(t *testing.T) {
	database, cleanDatabase := createTempFile(t, `[
		{"Name": "Cleo", "Wins": 10},
		{"Name": "Chris", "Wins": 33}]`)
	defer cleanDatabase()

	store := FileSystemPlayerStore{database}

	store.RecordWin("Pepper")

	got := store.GetPlayerScore("Pepper")
	want := 1
	assertScoreEquals(t, got, want)
})
```

## Пробуем запустить тест

```
=== RUN   TestFileSystemStore/store_wins_for_new_players#01
    --- FAIL: TestFileSystemStore/store_wins_for_new_players#01 (0.00s)
        file_system_store_test.go:86: got 0 want 1
```

## Пишем достаточно кода, чтобы тест прошел

Нам просто нужно обработать сценарий, когда `Find` возвращает `nil`, потому что он не смог найти игрока.

```go
//file_system_store.go
func (f *FileSystemPlayerStore) RecordWin(name string) {
	league := f.GetLeague()
	player := league.Find(name)

	if player != nil {
		player.Wins++
	} else {
		league = append(league, Player{name, 1})
	}

	f.database.Seek(0, io.SeekStart)
	json.NewEncoder(f.database).Encode(league)
}
```

"Счастливый путь" выглядит нормально, поэтому теперь мы можем попробовать использовать наше новое `Store` в интеграционном тесте. Это даст нам больше уверенности в том, что программное обеспечение работает, а затем мы сможем удалить избыточный `InMemoryPlayerStore`.

В `TestRecordingWinsAndRetrievingThem` заменяем старое хранилище.

```go
//server_integration_test.go
database, cleanDatabase := createTempFile(t, "")
defer cleanDatabase()
store := &FileSystemPlayerStore{database}
```

Если вы запустите тест, он должен пройти, и теперь мы можем удалить `InMemoryPlayerStore`. В `main.go` теперь появятся проблемы компиляции, что побудит нас использовать наше новое хранилище в "реальном" коде.

```go
// main.go
package main

import (
	"log"
	"net/http"
	"os"
)

const dbFileName = "game.db.json"

func main() {
	db, err := os.OpenFile(dbFileName, os.O_RDWR|os.O_CREATE, 0666)

	if err != nil {
		log.Fatalf("problem opening %s %v", dbFileName, err)
	}

	store := &FileSystemPlayerStore{db}
	server := NewPlayerServer(store)

	if err := http.ListenAndServe(":5000", server); err != nil {
		log.Fatalf("could not listen on port 5000 %v", err)
	}
}
```

- Мы создаем файл для нашей базы данных.
- Второй аргумент `os.OpenFile` позволяет определить разрешения для открытия файла: в нашем случае `O_RDWR` означает, что мы хотим читать и записывать, _и_ `os.O_CREATE` означает создать файл, если он не существует.
- Третий аргумент устанавливает права доступа к файлу: в нашем случае все пользователи могут читать и записывать файл. [(См. superuser.com для более подробного объяснения)](https://superuser.com/questions/295591/what-is-the-meaning-of-chmod-666).

Теперь запуск программы сохраняет данные в файле между перезапусками, ура!

## Дополнительный рефакторинг и вопросы производительности

Каждый раз, когда кто-то вызывает `GetLeague()` или `GetPlayerScore()`, мы читаем весь файл и разбираем его в JSON. Мы не должны этого делать, потому что `FileSystemStore` полностью отвечает за состояние лиги; он должен читать файл только при запуске программы и обновлять файл только при изменении данных.

Мы можем создать конструктор, который будет выполнять часть этой инициализации за нас и хранить лигу как значение в нашем `FileSystemStore` для использования при чтении вместо того, чтобы каждый раз считывать ее с диска.

```go
//file_system_store.go
type FileSystemPlayerStore struct {
	database io.ReadWriteSeeker
	league   League
}

func NewFileSystemPlayerStore(database io.ReadWriteSeeker) *FileSystemPlayerStore {
	database.Seek(0, io.SeekStart)
	league, _ := NewLeague(database)
	return &FileSystemPlayerStore{
		database: database,
		league:   league,
	}
}
```

Таким образом, нам нужно читать с диска только один раз. Теперь мы можем заменить все наши предыдущие вызовы для получения лиги с диска и просто использовать `f.league`.

```go
//file_system_store.go
func (f *FileSystemPlayerStore) GetLeague() League {
	return f.league
}

func (f *FileSystemPlayerStore) GetPlayerScore(name string) int {

	player := f.league.Find(name)

	if player != nil {
		return player.Wins
	}

	return 0
}

func (f *FileSystemPlayerStore) RecordWin(name string) {
	player := f.league.Find(name)

	if player != nil {
		player.Wins++
	} else {
		f.league = append(f.league, Player{name, 1})
	}

	f.database.Seek(0, io.SeekStart)
	json.NewEncoder(f.database).Encode(f.league)
}
```

Если вы попробуете запустить тесты, они теперь будут жаловаться на инициализацию `FileSystemPlayerStore`, поэтому просто исправьте их, вызвав наш новый конструктор.

### Еще одна проблема

Есть еще некоторая наивность в том, как мы работаем с файлами, что _могло бы_ создать очень неприятную ошибку в будущем.

Когда мы `RecordWin`, мы `Seek` обратно к началу файла, а затем записываем новые данные — но что, если новые данные были меньше, чем те, что были там раньше?

В нашем текущем случае это невозможно. Мы никогда не редактируем и не удаляем очки, поэтому данные могут только увеличиваться. Однако было бы безответственно оставлять код таким; не исключено, что может возникнуть сценарий удаления.

Как же мы это протестируем? Что нам нужно сделать, так это сначала провести рефакторинг нашего кода, чтобы отделить задачу _типа данных, которые мы записываем, от самой записи_. Затем мы сможем протестировать это отдельно, чтобы убедиться, что оно работает так, как мы надеемся.

Мы создадим новый тип, чтобы инкапсулировать нашу функциональность "когда мы записываем, мы начинаем с самого начала". Я назову его `Tape`. Создайте новый файл со следующим содержимым:

```go
// tape.go
package main

import "io"

type tape struct {
	file io.ReadWriteSeeker
}

func (t *tape) Write(p []byte) (n int, err error) {
	t.file.Seek(0, io.SeekStart)
	return t.file.Write(p)
}
```

Обратите внимание, что теперь мы реализуем только `Write`, поскольку он инкапсулирует часть `Seek`. Это означает, что наш `FileSystemStore` может просто иметь ссылку на `Writer` вместо этого.

```go
//file_system_store.go
type FileSystemPlayerStore struct {
	database io.Writer
	league   League
}
```

Обновите конструктор для использования `Tape`

```go
//file_system_store.go
func NewFileSystemPlayerStore(database io.ReadWriteSeeker) *FileSystemPlayerStore {
	database.Seek(0, io.SeekStart)
	league, _ := NewLeague(database)

	return &FileSystemPlayerStore{
		database: &tape{database},
		league:   league,
	}
}
```

Наконец, мы можем получить потрясающий результат, удалив вызов `Seek` из `RecordWin`. Да, это не кажется большим изменением, но, по крайней мере, это означает, что если мы будем выполнять другие виды записи, мы сможем полагаться на то, что наш `Write` будет вести себя так, как нам нужно. Кроме того, это позволит нам теперь протестировать потенциально проблемный код отдельно и исправить его.

Давайте напишем тест, в котором мы хотим обновить все содержимое файла чем-то, что меньше исходного содержимого.

## Сначала пишем тест

Наш тест создаст файл с некоторым содержимым, попробует записать в него с помощью `tape` и снова прочитает все, чтобы увидеть, что находится в файле. В `tape_test.go`:

```go
//tape_test.go
func TestTape_Write(t *testing.T) {
	file, clean := createTempFile(t, "12345")
	defer clean()

	tape := &tape{file}

	tape.Write([]byte("abc"))

	file.Seek(0, io.SeekStart)
	newFileContents, _ := io.ReadAll(file)

	got := string(newFileContents)
	want := "abc"

	if got != want {
		t.Errorf("got %q want %q", got, want)
	}
}
```

## Пробуем запустить тест

```
=== RUN   TestTape_Write
--- FAIL: TestTape_Write (0.00s)
    tape_test.go:23: got 'abc45' want 'abc'
```

Как мы и думали! Он записывает нужные нам данные, но оставляет остальную часть исходных данных.

## Пишем достаточно кода, чтобы тест прошел

У `os.File` есть функция truncate, которая позволит нам эффективно очистить файл. Мы должны просто вызвать ее, чтобы получить то, что нам нужно.

Измените `tape` следующим образом:

```go
//tape.go
type tape struct {
	file *os.File
}

func (t *tape) Write(p []byte) (n int, err error) {
	t.file.Truncate(0)
	t.file.Seek(0, io.SeekStart)
	return t.file.Write(p)
}
```

Компилятор выдаст ошибку в нескольких местах, где мы ожидаем `io.ReadWriteSeeker`, но передаем `*os.File`. К этому моменту вы уже должны уметь исправлять эти проблемы самостоятельно, но если вы застрянете, просто проверьте исходный код.

Как только вы это сделаете, наш тест `TestTape_Write` должен пройти!

### Еще один небольшой рефакторинг

В `RecordWin` у нас есть строка `json.NewEncoder(f.database).Encode(f.league)`.

Нам не нужно создавать новый кодировщик каждый раз, когда мы записываем; мы можем инициализировать его в нашем конструкторе и использовать его вместо этого.

Сохраните ссылку на `Encoder` в нашем типе и инициализируйте ее в конструкторе:

```go
//file_system_store.go
type FileSystemPlayerStore struct {
	database *json.Encoder
	league   League
}

func NewFileSystemPlayerStore(file *os.File) *FileSystemPlayerStore {
	file.Seek(0, io.SeekStart)
	league, _ := NewLeague(file)

	return &FileSystemPlayerStore{
		database: json.NewEncoder(&tape{file}),
		league:   league,
	}
}
```

Используйте это в `RecordWin`.

```go
func (f *FileSystemPlayerStore) RecordWin(name string) {
	player := f.league.Find(name)

	if player != nil {
		player.Wins++
	} else {
		f.league = append(f.league, Player{name, 1})
	}

	f.database.Encode(f.league)
}
```

## Разве мы только что не нарушили некоторые правила? Тестирование приватных вещей? Без интерфейсов?

### О тестировании приватных типов

Это правда, что _в целом_ следует отдавать предпочтение не тестированию приватных вещей, так как это иногда может привести к слишком сильной связи ваших тестов с реализацией, что может помешать рефакторингу в будущем.

Однако мы не должны забывать, что тесты должны давать нам _уверенность_.

Мы не были уверены, что наша реализация будет работать, если мы добавим какую-либо функциональность редактирования или удаления. Мы не хотели оставлять код таким, особенно если над ним работало более одного человека, который мог не знать о недостатках нашего первоначального подхода.

Наконец, это всего лишь один тест! Если мы решим изменить его работу, это не будет катастрофой, просто удалить тест, но мы, по крайней мере, зафиксировали требование для будущих сопровождающих.

### Интерфейсы

Мы начали код с использования `io.Reader`, так как это был самый простой путь для модульного тестирования нашего нового `PlayerStore`. По мере разработки кода мы перешли к `io.ReadWriter`, а затем к `io.ReadWriteSeeker`. Затем мы обнаружили, что в стандартной библиотеке нет ничего, что действительно реализовывало бы это, кроме `*os.File`. Мы могли бы принять решение написать свой собственный или использовать открытый исходный код, но прагматичным казалось просто создавать временные файлы для тестов.

Наконец, нам понадобился `Truncate`, который также есть в `*os.File`. Можно было бы создать свой собственный интерфейс, учитывающий эти требования.

```go
type ReadWriteSeekTruncate interface {
	io.ReadWriteSeeker
	Truncate(size int64) error
}
```

Но что это нам на самом деле дает? Имейте в виду, что мы _не имитируем_, и нереалистично для **файловой системы** хранилища принимать любой другой тип, кроме `*os.File`, поэтому нам не нужен полиморфизм, который дают интерфейсы.

Не бойтесь менять типы и экспериментировать, как мы это делали здесь. Отличная особенность использования статически типизированного языка заключается в том, что компилятор поможет вам при каждом изменении.

## Обработка ошибок

Прежде чем мы начнем работу над сортировкой, мы должны убедиться, что наш текущий код нас устраивает, и удалить любую техническую задолженность, которая у нас может быть. Важный принцип — как можно быстрее перейти к работающему программному обеспечению (избегать "красного" состояния), но это не означает, что мы должны игнорировать случаи ошибок!

Если мы вернемся к `FileSystemStore.go`, то увидим `league, _ := NewLeague(f.database)` в нашем конструкторе.

`NewLeague` может вернуть ошибку, если ему не удастся разобрать лигу из предоставленного нами `io.Reader`.

В тот момент было прагматично игнорировать это, поскольку у нас уже были падающие тесты. Если бы мы попытались заняться этим одновременно, мы бы жонглировали двумя вещами сразу.

Давайте сделаем так, чтобы наш конструктор мог возвращать ошибку.

```go
//file_system_store.go
func NewFileSystemPlayerStore(file *os.File) (*FileSystemPlayerStore, error) {
	file.Seek(0, io.SeekStart)
	league, err := NewLeague(file)

	if err != nil {
		return nil, fmt.Errorf("problem loading player store from file %s, %v", file.Name(), err)
	}

	return &FileSystemPlayerStore{
		database: json.NewEncoder(&tape{file}),
		league:   league,
	}, nil
}
```

Помните, очень важно давать полезные сообщения об ошибках (как и ваши тесты). Люди в интернете в шутку говорят, что большая часть Go-кода это:

```go
if err != nil {
	return err
}
```

**Это на 100% не идиоматично.** Добавление контекстной информации (т.е. того, что вы делали, чтобы вызвать ошибку) к вашим сообщениям об ошибках значительно облегчает работу с вашим программным обеспечением.

Если вы попробуете скомпилировать, вы получите несколько ошибок.

```
./main.go:18:35: multiple-value NewFileSystemPlayerStore() in single-value context
./file_system_store_test.go:35:36: multiple-value NewFileSystemPlayerStore() in single-value context
./file_system_store_test.go:57:36: multiple-value NewFileSystemPlayerStore() in single-value context
./file_system_store_test.go:70:36: multiple-value NewFileSystemPlayerStore() in single-value context
./file_system_store_test.go:85:36: multiple-value NewFileSystemPlayerStore() in single-value context
./server_integration_test.go:12:35: multiple-value NewFileSystemPlayerStore() in single-value context
```

В `main` мы захотим выйти из программы, распечатав ошибку.

```go
//main.go
store, err := NewFileSystemPlayerStore(db)

if err != nil {
	log.Fatalf("problem creating file system player store, %v ", err)
}
```

В тестах мы должны утверждать, что ошибок нет. Мы можем создать вспомогательную функцию для этого.

```go
//file_system_store_test.go
func assertNoError(t testing.TB, err error) {
	t.Helper()
	if err != nil {
		t.Fatalf("didn't expect an error but got one, %v", err)
	}
}
```

Разберитесь с остальными проблемами компиляции, используя эту вспомогательную функцию. Наконец, у вас должен быть падающий тест:

```
=== RUN   TestRecordingWinsAndRetrievingThem
--- FAIL: TestRecordingWinsAndRetrievingThem (0.00s)
    server_integration_test.go:14: didn't expect an error but got one, problem loading player store from file /var/folders/nj/r_ccbj5d7flds0sf63yy4vb80000gn/T/db841037437, problem parsing league, EOF
```

Мы не можем разобрать лигу, потому что файл пуст. Раньше мы не получали ошибок, потому что всегда просто игнорировали их.

Давайте исправим наш большой интеграционный тест, добавив в него валидный JSON:

```go
//server_integration_test.go
func TestRecordingWinsAndRetrievingThem(t *testing.T) {
	database, cleanDatabase := createTempFile(t, `[]`)
	//etc...
}
```

Теперь, когда все тесты проходят, нам нужно обработать сценарий, когда файл пуст.

## Сначала пишем тест

```go
//file_system_store_test.go
t.Run("works with an empty file", func(t *testing.T) {
	database, cleanDatabase := createTempFile(t, "")
	defer cleanDatabase()

	_, err := NewFileSystemPlayerStore(database)

	assertNoError(t, err)
})
```

## Пробуем запустить тест

```
=== RUN   TestFileSystemStore/works_with_an_empty_file
    --- FAIL: TestFileSystemStore/works_with_an_empty_file (0.00s)
        file_system_store_test.go:108: didn't expect an error but got one, problem loading player store from file /var/folders/nj/r_ccbj5d7flds0sf63yy4vb80000gn/T/db019548018, problem parsing league, EOF
```

## Пишем достаточно кода, чтобы тест прошел

Измените наш конструктор следующим образом:

```go
//file_system_store.go
func NewFileSystemPlayerStore(file *os.File) (*FileSystemPlayerStore, error) {

	file.Seek(0, io.SeekStart)

	info, err := file.Stat()

	if err != nil {
		return nil, fmt.Errorf("problem getting file info from file %s, %v", file.Name(), err)
	}

	if info.Size() == 0 {
		file.Write([]byte("[]"))
		file.Seek(0, io.SeekStart)
	}

	league, err := NewLeague(file)

	if err != nil {
		return nil, fmt.Errorf("problem loading player store from file %s, %v", file.Name(), err)
	}

	return &FileSystemPlayerStore{
		database: json.NewEncoder(&tape{file}),
		league:   league,
	}, nil
}
```

`file.Stat` возвращает статистику по нашему файлу, что позволяет нам проверить размер файла. Если он пуст, мы `Write` пустой JSON-массив и `Seek` обратно к началу, готовясь к остальному коду.

## Рефакторинг

Наш конструктор теперь немного запутан, поэтому давайте извлечем код инициализации в функцию:

```go
//file_system_store.go
func initialisePlayerDBFile(file *os.File) error {
	file.Seek(0, io.SeekStart)

	info, err := file.Stat()

	if err != nil {
		return fmt.Errorf("problem getting file info from file %s, %v", file.Name(), err)
	}

	if info.Size() == 0 {
		file.Write([]byte("[]"))
		file.Seek(0, io.SeekStart)
	}

	return nil
}
```

```go
//file_system_store.go
func NewFileSystemPlayerStore(file *os.File) (*FileSystemPlayerStore, error) {

	err := initialisePlayerDBFile(file)

	if err != nil {
		return nil, fmt.Errorf("problem initialising player db file, %v", err)
	}

	league, err := NewLeague(file)

	if err != nil {
		return nil, fmt.Errorf("problem loading player store from file %s, %v", file.Name(), err)
	}

	return &FileSystemPlayerStore{
		database: json.NewEncoder(&tape{file}),
		league:   league,
	}, nil
}
```

## Сортировка

Наш product owner хочет, чтобы `/league` возвращал игроков, отсортированных по их очкам, от наивысшего к наименьшему.

Основное решение, которое нужно принять здесь, — где в программном обеспечении это должно происходить. Если бы мы использовали "настоящую" базу данных, мы бы использовали такие вещи, как `ORDER BY`, чтобы сортировка была сверхбыстрой. По этой причине кажется, что реализации `PlayerStore` должны быть ответственными.

## Сначала пишем тест

Мы можем обновить утверждение в нашем первом тесте в `TestFileSystemStore`:

```go
//file_system_store_test.go
t.Run("league sorted", func(t *testing.T) {
	database, cleanDatabase := createTempFile(t, `[
		{"Name": "Cleo", "Wins": 10},
		{"Name": "Chris", "Wins": 33}]`)
	defer cleanDatabase()

	store, err := NewFileSystemPlayerStore(database)

	assertNoError(t, err)

	got := store.GetLeague()

	want := League{
		{"Chris", 33},
		{"Cleo", 10},
	}

	assertLeague(t, got, want)

	// read again
	got = store.GetLeague()
	assertLeague(t, got, want)
})
```

Порядок входящего JSON неверен, и наше `want` проверит, что он возвращен вызывающей стороне в правильном порядке.

## Пробуем запустить тест

```
=== RUN   TestFileSystemStore/league_from_a_reader,_sorted
    --- FAIL: TestFileSystemStore/league_from_a_reader,_sorted (0.00s)
        file_system_store_test.go:46: got [{Cleo 10} {Chris 33}] want [{Chris 33} {Cleo 10}]
        file_system_store_test.go:51: got [{Cleo 10} {Chris 33}] want [{Chris 33} {Cleo 10}]
```

## Пишем достаточно кода, чтобы тест прошел

```go
func (f *FileSystemPlayerStore) GetLeague() League {
	sort.Slice(f.league, func(i, j int) bool {
		return f.league[i].Wins > f.league[j].Wins
	})
	return f.league
}
```

[`sort.Slice`](https://golang.org/pkg/sort/#Slice)

> Slice сортирует предоставленный срез, используя предоставленную функцию less.

Легко!

## Подводим итоги

### Что мы рассмотрели

- Интерфейс `Seeker` и его связь с `Reader` и `Writer`.
- Работа с файлами.
- Создание простого в использовании помощника для тестирования с файлами, который скрывает все сложности.
- `sort.Slice` для сортировки срезов.
- Использование компилятора для безопасного внесения структурных изменений в приложение.

### Нарушение правил

- Большинство правил в разработке программного обеспечения на самом деле не правила, а просто лучшие практики, которые работают в 80% случаев.
- Мы обнаружили сценарий, когда одно из наших предыдущих "правил" — не тестировать внутренние функции — оказалось для нас бесполезным, поэтому мы нарушили это правило.
- Важно при нарушении правил понимать, на какой компромисс вы идете. В нашем случае, мы согласились на это, потому что это был всего один тест, и в противном случае было бы очень трудно отработать этот сценарий.
- Чтобы иметь возможность нарушать правила, **вы должны сначала их понять**. Аналогия с обучением игре на гитаре. Неважно, насколько креативным вы себя считаете, вы должны понимать и практиковать основы.

### Где находится наше программное обеспечение

- У нас есть HTTP API, где вы можете создавать игроков и увеличивать их счет.
- Мы можем вернуть лигу из результатов всех игроков в формате JSON.
- Данные сохраняются в файле JSON.