'use strict'
/* global Chat, ya */

class MainChat extends Chat {
  constructor () {
    super()
    this.names = null
    this.scrollElement = document.getElementById('scroll')
    this.scrollElement.addEventListener('click', () => this.startScroll())
    this.tts = null
  }

  error () {
    if (this.offset) {
      const message = { id: 'm', text: 'потеряно соединение.', classes: ['m'] }
      this.processMessage(message)
      this.render({ messages: message })
    }
    this.offset = 0
  }

  processMessage (message) {
    super.processMessage(message)
    if (message.id in this.icons) {
      this.names.forEach((name) => {
        if (message.text.search(name) !== -1) {
          message.classes.push('name')
        }
      })
    }
    if (this.tts && message.id === 'tts') {
      this.tts.push(message.text)
    }
  }

  refreshStats (data) {
    for (const k in data.stats) {
      document.getElementById(k).textContent = data.stats[k]
    }
    if (!this.names) {
      this.names = data.names
    }
    if (!this.tts && data.tts_api_key) {
      ya.speechkit.settings.apikey = data.tts_api_key
      this.tts = new Tts()
      setInterval(() => this.tts.worker(), 1000)
    }
  }

  startScroll () {
    this.isScroll = true
    this.scrollElement.classList.remove('active')
  }

  stopScroll () {
    this.isScroll = false
    this.scrollElement.classList.add('active')
  }
}

class Tts extends Array {
  constructor () {
    super()
    this.isBusy = false
    this.api = new ya.speechkit.Tts({
      speaker: 'omazh',
      stopCallback: () => {
        this.isBusy = false
      }
    })
  }

  worker () {
    if (!this.isBusy) {
      const message = this.shift()
      if (message) {
        this.isBusy = true
        this.api.speak(message)
      }
    }
  }
}

let chat

function main () {
  chat = new MainChat()
  chat.init()
  setInterval(() => chat.scroll(), 1000)
}

document.addEventListener('DOMContentLoaded', () => main())
document.addEventListener('keydown', (e) => {
  if (['PageUp', 'Home', 'ArrowUp'].indexOf(e.key) !== -1) {
    chat.stopScroll()
  }
})
document.addEventListener('mousedown', (e) => {
  if (e.clientX > document.body.clientWidth) {
    chat.stopScroll()
  }
})
document.addEventListener('touchstart', () => chat.stopScroll())
document.addEventListener('wheel', () => chat.stopScroll())
