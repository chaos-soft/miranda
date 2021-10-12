'use strict'
/* global Chat, get, ya */

class MainChat extends Chat {
  constructor () {
    super()
    this.scrollElement = document.getElementById('scroll')
    this.scrollElement.addEventListener('click', () => this.startScroll())
  }

  error () {
    if (this.offset) {
      this.render({ messages: 'Потеряно соединение' })
    }
    this.offset = 0
  }

  refreshStats (data) {
    for (const k in data.stats) {
      document.getElementById(k).textContent = data.stats[k]
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
let tts

function main () {
  chat = new MainChat()
  setInterval(() => {
    get(
      `http://localhost:55555/messages?offset=${chat.offset}`,
      (data) => chat.main(data),
      () => chat.error())
    get('http://localhost:55555/stats', (data) => chat.refreshStats(data))
  }, 5 * 1000)
  tts = new Tts()
  setInterval(() => {
    chat.scroll()
    tts.worker()
  }, 1000)
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
