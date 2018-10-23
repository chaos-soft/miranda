'use strict'
/* global ya, Chat, Message, get */
var names
var tts

class Tts extends Array {
  constructor () {
    super()
    this.isBusy = false
    var thisCache = this
    this.api = new ya.speechkit.Tts({
      speaker: 'omazh',
      stopCallback: function () {
        thisCache.isBusy = false
      }
    })
  }

  worker () {
    if (!this.isBusy) {
      var message = this.shift()
      if (message) {
        this.isBusy = true
        this.api.speak(message)
      }
    }
  }
}

class BaseChat extends Chat {
  constructor (element) {
    super(element)
    this.includeIds = ['p', 'e', 'm', 'js']
  }

  preLoop () {
    this.isScroll = false
  }

  postLoop () {
    if (this.isScroll) {
      this.scroll()
    }
  }

  preCreateDiv (message) {
    if (message['id'] === 'tts') {
      tts.push(message['text'])
    } else {
      new Message(message).replace()
    }
  }

  postCreateDiv (div, message) {
    var divStr = div.textContent
    names.forEach(function (name) {
      if (divStr.search(name) !== -1) {
        div.classList.add('m')
      }
    })
    this.isScroll = true
  }

  error () {
    if (this.offset) {
      var div = document.createElement('div')
      div.classList.add('m')
      div.textContent = 'Miranda: потеряно соединение.'
      this.element.appendChild(div)
      this.scroll()
    }
    this.offset = 0
  }
}

document.addEventListener('DOMContentLoaded', function () {
  var main = document.getElementById('main')
  var baseChat = new BaseChat(main)
  tts = new Tts()
  setInterval(function () {
    get(
      `/messages?offset=${baseChat.offset}`,
      function (data) {
        baseChat.core(data)
      },
      function () {
        baseChat.error()
      })
  }, 5 * 1000)
  setInterval(function () {
    tts.worker()
  }, 1000)
})
