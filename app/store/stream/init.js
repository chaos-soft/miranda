'use strict'
/* global Chat, get, Vue */
var app

class StreamChat extends Chat {
  preLoop () {
    app.i = 0
  }

  postLoop () {
    this.scroll(2 * 1000)
    setTimeout(function () {
      for (var i = app.$el.children.length - 1; i >= 0; i--) {
        var invisiblePart = app.$el.offsetHeight - window.innerHeight
        var div = app.$el.children[i]
        var divPart = div.offsetTop + div.offsetHeight
        if (divPart <= invisiblePart) {
          div.parentElement.removeChild(div)
        } else if (divPart - invisiblePart < 30) {
          div.classList.add('o0')
        }
      }
    }, 3 * 1000)
  }

  processMessage (message) {
    if (message.id === 'js' && message.text === 'clean_chat') {
      app.clean()
    } else if (message.id in this.icons) {
      app.show()
    }
  }

  emptyData () {
    app.hide()
  }
}

var init = function () {
  var streamChat = new StreamChat()
  setInterval(function () {
    get(
      `/messages?offset=${streamChat.offset}`,
      function (data) {
        streamChat.core(data)
      })
  }, 5 * 1000)
}

document.addEventListener('DOMContentLoaded', function () {
  app = new Vue({
    el: '#main',
    data: { messages: [], i: 0 },
    mounted: function () {
      this.$nextTick(init)
    },
    methods: {
      clean: function () {
        this.messages = []
        this.$el.classList.add('o0')
      },
      hide: function () {
        this.i += 1
        if (this.i === 12) {
          this.$el.classList.add('o0')
        }
      },
      show: function () {
        this.$el.classList.remove('o0')
      }
    },
    computed: {
      getMessages: function () {
        return this.messages.filter(function (message) {
          return ['tts', 'm', 'js'].indexOf(message.id) === -1
        })
      }
    }
  })
})
