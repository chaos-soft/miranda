icons = {'t': 't.ico', 'g': 'g.png', 's': 's.ico'};

message_pattern = `<img src="/store/icons/{{ icon }}" alt="">
<span>{{ name }}</span>: {{ text }}`;

core = function(data) {
    if (! data.length) {
        chat.hide();
    } else {
        chat.i = 0;
        chat.offset += data.length;

        for (var i = 0; i < data.length; i++) {
            var div = undefined;

            if ('replacements' in data[i]) {
                for (var k in data[i]['replacements']) {
                    var img = '<img src="' + data[i]['replacements'][k] + '" alt="">';
                    var r = RegExp(k, 'g');
                    data[i]['text'] = data[i]['text'].replace(r, img);
                }
            }

            if (data[i]['id'] in icons) {
                var div = document.createElement('div');
                div.classList.add(data[i]['id']);
                div.innerHTML = message_pattern.
                    replace('{{ icon }}', icons[data[i]['id']]).
                    replace('{{ name }}', data[i]['name']).
                    replace('{{ text }}', data[i]['text']);

                if ('color' in data[i]) {
                    div.children[1].style.color = data[i]['color'];
                }
            } else if (data[i]['id'] === 'js') {
                try {
                    eval(data[i]['command']);
                } catch(e) {
                    console.log(e);
                }
            } else if (data[i]['id'] === 'p' || data[i]['id'] === 'e') {
                var div = document.createElement('div');
                div.classList.add('m');
                div.innerHTML = data[i]['name'] + ': ' + data[i]['text'];
            }

            if (div) {
                chat.c[0].appendChild(div);
                chat.removeClass('o0');
            }
        }

        setTimeout(function() {
            chat.animate({scrollTop: chat[0].scrollHeight}, 2 * 1000, function() {
                chat.c.children().each(function() {
                    var current = $(this);
                    var position = current.offset()['top'] + current.outerHeight();
                    if (position < 20) {
                        current.remove();
                    } else if (position < 50) {
                        current.addClass('o0');
                    }
                });
            });
        }, 2 * 1000);
    }
}

$(function() {
    chat = $('#chat');
    chat.c = chat.children();
    chat.offset = 0;
    chat.i = 0;
    chat.clean = function() {
        chat.c.children().remove();
        chat.addClass('o0');
    };
    chat.hide = function() {
        chat.i += 1;
        if (chat.i === 12) {
            chat.addClass('o0');
        }
    };

    setInterval(function() {
        $.get('/comments', {offset: chat.offset}, core).fail(function() {
            chat.offset = 0;
        });
    }, 5 * 1000);
});
