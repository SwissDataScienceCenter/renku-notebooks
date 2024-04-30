package main

import (
	"log"

	"github.com/SwissDataScienceCenter/renku-notebooks/git-https-proxy/config2"
)

func main() {
	config, err := config2.GetConfig()
	if err != nil {
		log.Fatalln(err)
	}

	log.Println(config)
}
