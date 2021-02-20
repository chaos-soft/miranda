'use strict'
/* global Chat, get */

class StreamChat extends Chat {
  constructor () {
    super()
    // На 12 чат скрывается.
    this.i = 0
    this.offset = -5
    this.systemIds = ['p', 'e']
  }

  clean () {
    super.clean()
    this.hide()
  }

  emptyData () {
    this.i += 1
    if (this.i === 12) {
      this.hide()
    }
  }

  hide () {
    this.main.classList.add('o0')
  }

  preLoop () {
    this.i = 0
  }

  postLoop () {
    setTimeout(() => {
      for (const div of this.main.querySelectorAll(':scope > div')) {
        const mainLastInvisiblePixel = this.main.offsetHeight - window.innerHeight
        const divLastPixel = div.offsetTop + div.offsetHeight
        if (divLastPixel <= mainLastInvisiblePixel) {
          div.remove()
        } else if (divLastPixel - mainLastInvisiblePixel < 30) {
          div.classList.add('o0')
        }
      }
    }, 3 * 1000)
  }

  processMessage (message) {
    super.processMessage(message)
    if (message.id in this.icons) {
      this.show()
    }
    message.getColor = () => {
      if ('color' in message) {
        return `color: ${message.color}`
      }
    }
  }

  show () {
    this.main.classList.remove('o0')
  }
}

let chat

function init () {
  chat = new StreamChat()
  setInterval(() => {
    get(
      `/messages?offset=${chat.offset}`,
      (data) => chat.core(data))
  }, 5 * 1000)
  setInterval(() => chat.scroll(), 1000)
}

document.addEventListener('DOMContentLoaded', () => init())
