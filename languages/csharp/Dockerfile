FROM mcr.microsoft.com/dotnet/sdk:5.0-buster-slim
RUN dotnet new console --force -o Main && rm /Main/Program.cs
COPY compile.sh run.sh /