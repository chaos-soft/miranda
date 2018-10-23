'use strict'
/* global Chat, Message, get */

class StreamChat extends Chat {
  constructor (element) {
    super(element)
    this.includeIds = ['p', 'e']
  }

  preLoop () {
    this.element.i = 0
  }

  postLoop () {
    this.scroll(2 * 1000)
    var thisCache = this
    setTimeout(function () {
      for (var i = thisCache.element.children.length - 1; i >= 0; i--) {
        var invisiblePart = thisCache.element.offsetHeight - window.innerHeight
        var div = thisCache.element.children[i]
        var divPart = div.offsetTop + div.offsetHeight
        if (divPart <= invisiblePart) {
          div.parentElement.removeChild(div)
        } else if (divPart - invisiblePart < 30) {
          div.classList.add('o0')
        }
      }
    }, 3 * 1000)
  }

  preCreateDiv (message) {
    if (message['id'] === 'js' && message['text'] === 'clean_chat') {
      this.element.clean()
    } else {
      new Message(message).replace()
    }
  }

  postCreateDiv (div, message) {
    if ('color' in message) {
      div.children[1].style.color = message['color']
    }
    this.element.show()
  }

  emptyData () {
    this.element.hide()
  }
}

var getMain = function () {
  var main = document.getElementById('main')
  main.i = 0

  main.clean = function () {
    this.innerHTML = ''
    this.classList.add('o0')
  }

  main.hide = function () {
    this.i += 1
    if (this.i === 12) {
      this.classList.add('o0')
    }
  }

  main.show = function () {
    this.classList.remove('o0')
  }

  return main
}

document.addEventListener('DOMContentLoaded', function () {
  var streamChat = new StreamChat(getMain())
  setInterval(function () {
    get(
      `/messages?offset=${streamChat.offset}`,
      function (data) {
        streamChat.core(data)
      })
  }, 5 * 1000)
})
