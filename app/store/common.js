'use strict'
/* global XMLHttpRequest, scrollTo, Global, app */

window.get = function (url, callbackSuccess, callbackError) {
  var xhr = new XMLHttpRequest()
  xhr.addEventListener('load', function () {
    if (xhr.status === 200) {
      callbackSuccess(JSON.parse(this.responseText))
    }
  })
  xhr.addEventListener('error', function () {
    if (callbackError) {
      callbackError()
    }
  })
  xhr.open('GET', url, true)
  xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest')
  xhr.send()
}

window.Chat = class {
  constructor () {
    this.offset = 0
    this.icons = { t: 't.ico', g: 'g.png', s: 's.ico', y: 'y.png' }
  }

  preLoop () {
  }

  postLoop () {
  }

  processMessage (message) {
  }

  emptyData () {
  }

  core (data) {
    this.offset = data.total
    if (!data.messages.length) {
      this.emptyData()
      return
    }
    this.preLoop()
    var thisCache = this
    data.messages.forEach(function (message) {
      message.classes = [message.id]
      if (message.id in thisCache.icons) {
        message.icon = thisCache.icons[message.id]
        new Message(message).replace()
      }
      thisCache.processMessage(message)
      app.messages.push(message)
    })
    this.postLoop()
  }

  scroll (timeout = 200) {
    setTimeout(function () {
      scrollTo(0, app.$el.scrollHeight)
    }, timeout)
  }
}

var Message = class {
  constructor (message) {
    this.message = message
    this.replacements = 'replacements' in message ? message.replacements : []
    this.reSmile = /:\w+:/gi
  }

  prepareG () {
    var m = this.message.text.match(this.reSmile)
    if (m) {
      var thisCache = this
      m.forEach(function (replacement) {
        var smileName = replacement.slice(1, -1)
        var isFound = false
        Global.Smiles.some(function (smile) {
          if (smile.name === smileName) {
            thisCache.replacements.push([
              replacement,
              smile.animated ? smile.img_gif : smile.img_big
            ])
            isFound = true
            return true
          }
        })
        if (!isFound) {
          thisCache.message.premiums.some(function (id) {
            if (id in Global.Channel_Smiles) {
              Global.Channel_Smiles[id].some(function (smile) {
                if (smile.name === smileName) {
                  thisCache.replacements.push([
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

  prepareS () {
    var m = this.message.text.match(this.reSmile)
    if (m) {
      var thisCache = this
      m.forEach(function (replacement) {
        var smileName = replacement.slice(1, -1)
        thisCache.replacements.push([
          replacement,
          `https://sc2tv.ru/images/smiles/${smileName}.png`
        ])
      })
    }
  }

  prepareT () {
    var thisCache = this
    this.message.emotes.split('/').forEach(function (emote) {
      var idIndexes = emote.split(':')
      idIndexes[1].split(',').forEach(function (i) {
        i = i.split('-')
        thisCache.replacements.push([
          thisCache.message.text.substring(parseInt(i[0]), parseInt(i[1]) + 1),
          `https://static-cdn.jtvnw.net/emoticons/v1/${idIndexes[0]}/1.0`
        ])
      })
    })
  }

  replace_ () {
    var search
    var img
    var thisCache = this
    this.replacements.reverse().forEach(function (replacement) {
      if (replacement.length === 2) {
        search = replacement[0]
        img = `<img src="${replacement[1]}">`
      } else {
        search = replacement
        img = `<img src="${replacement}">`
      }
      thisCache.message.text = thisCache.message.text.replace(search, img)
    })
  }

  replace () {
    if (this.message.id === 'g') {
      this.prepareG()
    } else if (this.message.id === 's') {
      this.prepareS()
    } else if (this.message.id === 't' && this.message.emotes) {
      this.prepareT()
    }
    this.replace_()
  }
}
