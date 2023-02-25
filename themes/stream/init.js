'use strict'
/* global Chat */

class StreamChat extends Chat {
  constructor () {
    super()
    // На 12 чат скрывается.
    this.i = 0
    this.offset = -10
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

  error () {
    this.emptyData()
  }

  hide () {
    this.main_.classList.add('o0')
  }

  preLoop () {
    this.i = 0
  }

  postLoop () {
    setTimeout(() => {
      for (const div of this.main_.querySelectorAll(':scope > div')) {
        const mainLastInvisiblePixel = this.main_.offsetHeight - window.innerHeight
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
  }

  show () {
    this.main_.classList.remove('o0')
  }
}

function main () {
  const chat = new StreamChat()
  chat.init()
  setInterval(() => chat.scroll(), 1000)
}

document.addEventListener('DOMContentLoaded', () => main())
