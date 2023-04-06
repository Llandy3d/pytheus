# Quickstart

Here we will build piece by piece the introductory example while explaining what the differences pieces are doing, we will end with loading the redis backend where you will see that it's a matter of just loading a different backend with a function call :)

We will be using [Flask](https://flask.palletsprojects.com) to create a small api service where we monitor the time it takes for an endpoint to respond and we will have a slow one on purpose so that we have some different data to query when scraped by prometheus!

!!! note

    if you download the source repo for the pytheus project, you can use the included `docker-compose.yaml` file to spin up a redis & prometheus instance already configured that will pick up your metrics so that you can interactively explore them!

    Or you can always configure prometheus yourself to scrape the `/metrics` endpoint :)
