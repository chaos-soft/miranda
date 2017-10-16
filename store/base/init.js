icons = {'t': 't.ico', 'g': 'g.png', 's': 's.ico', 'y': 'y.png'};
names = [];

message_pattern = `<img src="/store/icons/{{ icon }}" alt="">
<span>{{ name }}</span>: {{ text }}`;

tts = [];
tts.is_busy = false;
tts.worker = function() {
    if (tts.api_key && ! tts.is_busy) {
        if (typeof tts.y === 'undefined') {
            tts.y = new ya.speechkit.Tts({
                apikey: tts.api_key,
                speaker: 'omazh',
                stopCallback: function() {
                    tts.is_busy = false;
                },
            });
        }

        var message = tts.shift();
        if (message) {
            tts.is_busy = true;
            tts.y.speak(message);
        }
    }
};

core = function(data) {
    if (! data.length) {
        return;
    }

    main.offset += data.length;
    html_body.is_scroll = false;

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
        } else if (data[i]['id'] === 'js') {
            try {
                eval(data[i]['command']);
            } catch(e) {
                console.log(e);
            }
        } else {
            var div = document.createElement('div');
            div.classList.add('m');
            div.innerHTML = 'Miranda: ' + data[i]['text'];
        }

        if (div) {
            var div_str = div.toString();

            for (var i2 = 0; i2 < names.length; i2++) {
                if (div_str.search(names[i2]) !== -1) {
                    div.classList.add('m');
                }
            }

            main[0].appendChild(div);
            html_body.is_scroll = true;
        }
    }

    if (html_body.is_scroll) {
        html_body.animate({scrollTop: main[0].scrollHeight}, 1000);
    }
};

setInterval(function() {
    tts.worker();
}, 100);

$(function() {
    html_body = $('html, body');

    main = $('#main');
    main.offset = 0;

    setInterval(function() {
        $.get('/comments', {'offset': main.offset}, core).fail(function() {
            if (main.offset) {
                m = '<div class="m">Miranda: потеряно соединение.</div>';
                main.append(m);
            }

            main.offset = 0;
        });
    }, 5 * 1000);
});
