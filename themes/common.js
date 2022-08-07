'use strict'
/* global Global, Mustache, WebSocket */

class Chat {
  constructor () {
    this.icons = { g: 'g.png', t: 't.ico', w: 'w.png' }
    this.isClean = false
    this.isScroll = true
    this.main_ = document.getElementsByClassName('main')[0]
    this.messages = document.getElementById('messages').innerHTML
    this.offset = 0
    this.systemIds = ['e', 'm', 'p']
    this.url = 'ws://localhost:55555'
    this.url = `wss://${window.location.host}/miranda/`
  }

  clean () {
    this.isClean = false
    this.main_.querySelectorAll(':scope > div').forEach((div) => div.remove())
  }

  emptyData () {
  }

  error () {
  }

  init () {
    const w = new WebSocket(this.url)
    w.addEventListener('close', () => {
      clearInterval(interval)
      this.error()
      setTimeout(() => {
        this.init()
      }, 5 * 1000)
    })
    w.addEventListener('message', (e) => {
      this.main(JSON.parse(e.data))
    })
    const interval = setInterval(() => {
      if (w.readyState === w.OPEN) {
        w.send(JSON.stringify({ offset: this.offset }))
      }
    }, 5 * 1000)
  }

  main (data) {
    this.refreshStats(data)
    this.offset = data.total
    if (!data.messages.length) {
      this.emptyData()
      return
    }
    this.preLoop()
    data.messages.forEach((message) => this.processMessage(message))
    if (this.isClean) {
      this.clean()
    }
    this.render(data)
    this.postLoop()
  }

  postLoop () {
  }

  preLoop () {
  }

  processMessage (message) {
    message.classes = [message.id]
    if (message.id === 'js' && message.text === 'clean_chat') {
      this.isClean = true
    } else if (message.id in this.icons) {
      message.icon = this.icons[message.id]
      new Message(message).replace()
    }
    message.getClasses = () => message.classes.join(' ')
    message.getColor = () => {
      if ('color' in message) {
        return `color: ${message.color}`
      }
    }
    message.isNormal = () => {
      if (message.id in this.icons) {
        return true
      }
    }
    message.isSystem = () => {
      if (this.systemIds.indexOf(message.id) !== -1) {
        return true
      }
    }
  }

  refreshStats () {
  }

  render (data) {
    this.main_.insertAdjacentHTML('beforeend', Mustache.render(this.messages, data))
  }

  scroll () {
    if (this.isScroll) {
      const main = this.main_.offsetTop + this.main_.scrollHeight
      const window_ = window.innerHeight + window.scrollY
      if (main !== window_) {
        window.scroll(0, main)
      }
    }
  }
}

class Message {
  constructor (message) {
    this.message = message
    this.replacements = 'replacements' in message ? message.replacements : []
    this.reSmile = /:\w+:/gi
  }

  prepareG () {
    const m = this.message.text.match(this.reSmile)
    if (m) {
      m.forEach((replacement) => {
        const smileName = replacement.slice(1, -1)
        let isFound = false
        Global.Smiles.some((smile) => {
          if (smile.name === smileName) {
            this.replacements.push([
              replacement,
              smile.animated ? smile.img_gif : smile.img_big
            ])
            isFound = true
            return true
          }
        })
        if (!isFound) {
          this.message.premiums.some((id) => {
            if (id in Global.Channel_Smiles) {
              Global.Channel_Smiles[id].some((smile) => {
                if (smile.name === smileName) {
                  this.replacements.push([
                    replacement,
                    smile.animated ? smile.img_gif : smile.img_big
                  ])
                  isFound = true
                  return true
                }
              })
              if (isFound) {
                return true
              }
            }
          })
        }
      })
    }
  }

  prepareT () {
    for (const r of this.replacements) {
      if (r.length === 2) {
        r[1] = `https://static-cdn.jtvnw.net/emoticons/v1/${r[1]}/1.0`
      }
    }
  }

  replace_ () {
    let img
    let search
    this.replacements.forEach((replacement) => {
      if (replacement.length === 2) {
        img = `<img src="${replacement[1]}">`
        search = new RegExp(replacement[0], 'gi')
      } else {
        img = `<img src="${replacement}">`
        search = replacement
      }
      this.message.text = this.message.text.replace(search, img)
    })
  }

  replace () {
    if (this.message.id === 'g') {
      this.prepareG()
    } else if (this.message.id === 't') {
      this.prepareT()
    }
    this.replace_()
  }
}
