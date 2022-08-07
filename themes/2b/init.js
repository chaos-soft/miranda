'use strict'
/* global Chat */

class TwoBChat extends Chat {
  constructor () {
    super()
    this.offset = -10
    this.systemIds = ['p', 'e']
  }

  emptyData () {
    this.removeMessages()
  }

  preLoop () {
    this.removeMessages()
  }

  postLoop () {
    setTimeout(() => {
      for (const div of this.main_.querySelectorAll(':scope > .o0')) {
        div.classList.remove('o0')
      }
    }, 100)
  }

  removeMessages () {
    for (const div of this.main_.querySelectorAll(':scope > div')) {
      if (div.classList.contains('remove')) {
        div.remove()
      } else {
        div.classList.add('remove')
        div.style.marginTop = `-${div.offsetHeight}px`
      }
    }
  }
}

document.addEventListener('DOMContentLoaded', () => new TwoBChat().init())
