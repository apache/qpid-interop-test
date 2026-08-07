# Bug Reproducers

Minimal standalone scripts that demonstrate each client library bug found by QIT 2.0. See [../CLIENT_BUGS.md](../CLIENT_BUGS.md) for the full writeup.

All scripts require an Artemis broker on localhost:5672 with user/pass artemis/artemis.

## Java (ProtonJ2) repros

```bash
mvn dependency:copy-dependencies
javac -cp "target/dependency/*" protonj2-list-null-npe.java
java -cp ".:target/dependency/*" ProtonJ2ListNullNpe
```

## .NET repros

Create a project, add the package reference, then copy in the .cs file:
```bash
dotnet new console -o repro && cd repro
dotnet add package Apache.Qpid.Proton.Client --version 1.0.0
cp ../dotnet-list-null-nre.cs Program.cs
dotnet run
```

## JavaScript (Rhea) repros

```bash
npm install rhea
node rhea-ulong-precision.js
```
