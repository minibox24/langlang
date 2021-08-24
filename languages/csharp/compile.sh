dotnet new console --force -o Main 1> /dev/null && \
    cp Main.cs /Main/Program.cs && \
    dotnet publish Main --configuration Release