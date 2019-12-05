'use strict'
/* global ya, Chat, get, Vue */
var names
var tts
var app

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
  postLoop () {
    if (app.isScroll) {
      this.scroll()
    }
  }

  processMessage (message) {
    names.forEach(function (name) {
      if (message.text.search(name) !== -1) {
        if (message.classes.indexOf('m') === -1) {
          message.classes.push('m')
        }
      }
    })
    if (message.id === 'tts') {
      tts.push(message.text)
    }
  }

  error () {
    if (this.offset) {
      app.messages.push({ id: 'm', text: 'потеряно соединение.', classes: ['m'] })
      this.scroll()
    }
    this.offset = 0
  }
}

var init = function () {
  var baseChat = new BaseChat()
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
}

document.addEventListener('DOMContentLoaded', function () {
  app = new Vue({
    el: '#main',
    data: { messages: [], isScroll: true },
    mounted: function () {
      this.$nextTick(init)
    },
    computed: {
      getMessages: function () {
        return this.messages.filter(function (message) {
          return message.id !== 'tts'
        })
      }
    },
    methods: {
      toggleScroll: function () {
        this.isScroll = !this.isScroll
      }
    }
  })
})
