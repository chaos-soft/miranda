var icons = {t: 't.ico', g: 'g.png', s: 's.ico', y: 'y.png'}
var main

var messagePattern = `<img src="/store/icons/{{ icon }}" alt="">
<span>{{ name }}</span>: {{ text }}`

var core = function (data) {
  if (! data.length) {
    main.hide()
    return
  }

  main.i = 0
  main.offset += data.length

  data.forEach(function (item) {
    var div

    if ('replacements' in item) {
      for (var k in item['replacements']) {
        var img = '<img src="' + item['replacements'][k] + '" alt="">'
        var r = RegExp(k, 'g')
        item['text'] = item['text'].replace(r, img)
      }
    }

    if (item['id'] in icons && ! ('is_muted' in item)) {
      div = document.createElement('div')
      div.classList.add(item['id'])
      div.innerHTML = messagePattern
        .replace('{{ icon }}', icons[item['id']])
        .replace('{{ name }}', item['name'])
        .replace('{{ text }}', item['text'])

        if ('color' in item) {
          div.children[1].style.color = item['color']
        }
    } else if (item['id'] === 'js') {
      try {
        eval(item['command'])
      } catch (e) {
        console.log(e)
      }
    } else if (item['id'] === 'p' || item['id'] === 'e') {
      div = document.createElement('div')
      div.classList.add('m')
      div.innerHTML = 'Miranda: ' + item['text']
    }

    if (div) {
      main.children[0].appendChild(div)
      main.show()
    }
  })

  setTimeout(function () {
    main.scrollTo(0, main.scrollHeight)
  }, 2 * 1000)
  setTimeout(function () {
    for (var i = main.children[0].children.length - 1; i >= 0; i--) {
      var hiddenPart = main.children[0].offsetHeight - main.offsetHeight
      var div = main.children[0].children[i]
      var divPart = div.offsetTop + div.offsetHeight

      if (divPart <= hiddenPart) {
        div.parentElement.removeChild(div)
      } else if (divPart - hiddenPart < 30) {
        div.classList.add('o0')
      }
    }
  }, 3 * 1000)
}

var error = function () {
  main.offset = 0
}

document.addEventListener('DOMContentLoaded', function () {
  main = document.getElementById('main')
  main.offset = 0
  main.i = 0
  main.clean = function () {
    main.children[0].innerHTML = ''
    main.classList.add('o0')
  }
  main.hide = function () {
    main.i += 1

    if (main.i === 12) {
      main.classList.add('o0')
    }
  }
  main.show = function () {
    main.classList.remove('o0')
  }

  setInterval(function () {
    window.get('/comments?offset=' + main.offset, core, error)
  }, 5 * 1000)
})
