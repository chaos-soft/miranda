'use strict'
/* global Chat, get, names, ya */

class BaseChat extends Chat {
  constructor () {
    super()
    this.scrollElement = document.getElementById('scroll')
    this.scrollElement.addEventListener('click', () => this.startScroll())
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
      names.every((name) => {
        if (message.text.search(name) !== -1) {
          message.classes.push('name')
          return false
        }
      })
    }
    if (message.id === 'tts') {
      tts.push(message.text)
    }
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

function init () {
  chat = new BaseChat()
  setInterval(() => {
    get(
      `messages?offset=${chat.offset}`,
      (data) => chat.core(data),
      () => chat.error())
  }, 5 * 1000)
  setInterval(() => chat.scroll(), 1000)
  setInterval(() => get('stats', (data) => chat.refreshStats(data)), 60 * 1000)
  tts = new Tts()
  setInterval(() => tts.worker(), 1000)
}

document.addEventListener('DOMContentLoaded', () => init())
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
