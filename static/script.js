function downloadTextFile(filename, content){
    // Ініціює звичайне завантаження файлу в браузері користувача (у папку
    // "Завантаження" на його пристрої) — без жодного запису на диск сервера.
    // Працює однаково і локально, і на реальному хостингу.
    // На початку файлу додаємо UTF-8 BOM (керівний символ U+FEFF) — без нього
    // прості текстові редактори (напр. Notepad) не завжди розпізнають
    // кодування і показують українські літери "ієрогліфами" замість тексту.
    let bom = String.fromCharCode(0xFEFF);
    let blob = new Blob([bom + content], { type: "text/plain;charset=utf-8" });
    let url = URL.createObjectURL(blob);
    let a = document.createElement("a");
    a.href = url;
    a.download = filename || "файл.txt";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}


async function getVerse(){


    let book = document.getElementById("book").value;

    let chapter = document.getElementById("chapter").value;

    let verse = document.getElementById("verse").value;

    let verseTo = document.getElementById("verse-to").value;


    if (!chapter || !verse) return;


    let toast = document.getElementById("loading-toast");
    toast.classList.add("show");

    let data;

    try {

        let response = await fetch("/verse", {

            method:"POST",

            headers:{
                "Content-Type":"application/json"
            },


            body:JSON.stringify({

                book:book,
                chapter:parseInt(chapter),
                verse:parseInt(verse),
                verse_to: verseTo ? parseInt(verseTo) : null

            })

        });

        data = await response.json();

    } catch (err) {

        toast.classList.remove("show");
        let resultDiv = document.getElementById("result");
        document.getElementById("form-section").style.display = "none";
        document.getElementById("result-section").style.display = "block";
        resultDiv.innerHTML = "Помилка з'єднання із сервером. Спробуйте ще раз.";
        return;

    }


    let resultDiv = document.getElementById("result");
    document.getElementById("keyword-notes").innerHTML = "";
    window.__keywords = {};
    window.__notes = {};
    window.__conclusions = {};
    window.__selection = new Set();
    window.__activeWord = null;
    window.__wordIndex = null;
    if(window.__colorPicker) hideColorPicker();
    if(window.__selectionBar) hideSelectionBar();


    if (data.verses) {
        resultDiv.innerHTML = "";
        let frag = document.createDocumentFragment();
        data.verses.forEach(v => {
            let line = document.createElement("div");
            line.className = "verse-line";
            let wordsHtml = `<span class="verse-num">${v.number}.</span>` + highlightWords(v.text);
            line.innerHTML = wordsHtml;
            frag.appendChild(line);
        });
        resultDiv.appendChild(frag);
    } else {
        resultDiv.innerHTML = highlightWords(data.text);
    }

    // Індексуємо всі слова одразу після рендеру — щоб позначення
    // ключового слова далі спрацьовувало миттєво, без пошуку по всьому тексту.
    buildWordIndex();

    document.getElementById("form-section").style.display = "none";
    document.getElementById("result-section").style.display = "block";
    toast.classList.remove("show");

}


function highlightWords(text){
    let words = text.split(/\s+/);
    return words.map(w =>
        `<span class="word" onclick="pickWord(this, event)">${w}</span>`
    ).join(" ");
}


function normalizeWord(text){
    // Прибираємо розділові знаки з країв слова (кому, крапку, лапки тощо),
    // щоб "Бог" і "Бог," (в кінці речення) вважались одним і тим самим словом
    // і фарбувались одним кольором. Символи всередині слова (напр. апостроф
    // в "об'явлення") не чіпаємо.
    return (text || "").trim().replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "");
}


function buildWordIndex(){
    // Мапа "слово" -> масив всіх його елементів у тексті.
    // Дозволяє миттєво (без обходу всього DOM) пофарбувати всі
    // однакові слова при виборі ключового слова.
    let resultDiv = document.getElementById("result");
    let index = new Map();
    if(resultDiv){
        resultDiv.querySelectorAll(".word").forEach(span => {
            let key = normalizeWord(span.textContent);
            if(!key) return;
            if(!index.has(key)) index.set(key, []);
            index.get(key).push(span);
        });
    }
    window.__wordIndex = index;
}


function pickWord(el, evt){
    // Ctrl/Cmd + клік — додати слово до множинного вибору,
    // щоб потім позначити ключовими одразу декілька (різних) слів.
    if(evt && (evt.ctrlKey || evt.metaKey)){
        evt.stopPropagation();
        toggleSelection(el);
        return;
    }

    // Звичайний клік скасовує активний множинний вибір
    if(window.__selection && window.__selection.size > 0){
        clearSelection();
    }

    if(window.__colorPicker) hideColorPicker();

    // Підсвічуємо нове активне слово й одразу відкриваємо палітру кольорів —
    // без проміжного контекстного меню, щоб вибір ключового слова займав один клік.
    window.__activeWord = el;
    el.classList.add("active");

    showColorPicker("single", el);
}


function toggleSelection(el){
    let word = (el.textContent || "").trim();
    if(!word) return;

    if(window.__colorPicker) hideColorPicker();
    if(window.__activeWord){
        window.__activeWord.classList.remove("active");
        window.__activeWord = null;
    }

    if(!window.__selection) window.__selection = new Set();

    if(window.__selection.has(el)){
        window.__selection.delete(el);
        el.classList.remove("selected");
    } else {
        window.__selection.add(el);
        el.classList.add("selected");
    }

    updateSelectionBar();
}


function clearSelection(){
    if(window.__selection){
        window.__selection.forEach(el => {
            if(el.classList) el.classList.remove("selected");
        });
        window.__selection.clear();
    }
    hideSelectionBar();
}


function updateSelectionBar(){
    let count = window.__selection ? window.__selection.size : 0;

    if(count === 0){
        hideSelectionBar();
        return;
    }

    if(!window.__selectionBar){
        let bar = document.createElement("div");
        bar.className = "selection-bar";
        window.__selectionBar = bar;
        document.body.appendChild(bar);
    }

    let bar = window.__selectionBar;
    bar.innerHTML = "";

    let label = document.createElement("span");
    label.className = "selection-bar-label";
    label.textContent = count === 1
        ? "Вибрано 1 слово"
        : `Вибрано слів: ${count}`;

    let btnAdd = document.createElement("button");
    btnAdd.className = "selection-bar-btn selection-bar-btn-primary";
    btnAdd.textContent = "Додати до ключових слів";
    btnAdd.onclick = (e) => {
        e.stopPropagation();
        showColorPicker("multi", btnAdd);
    };

    let btnCancel = document.createElement("button");
    btnCancel.className = "selection-bar-btn";
    btnCancel.textContent = "Скасувати";
    btnCancel.onclick = (e) => {
        e.stopPropagation();
        clearSelection();
    };

    bar.appendChild(label);
    bar.appendChild(btnAdd);
    bar.appendChild(btnCancel);
}


function hideSelectionBar(){
    if(window.__selectionBar){
        window.__selectionBar.remove();
        window.__selectionBar = null;
    }
}


function positionMenu(menu, el){
    let rect = el.getBoundingClientRect();
    let menuRect = menu.getBoundingClientRect();

    // За замовчуванням — праворуч від слова
    let left = rect.right + 8;
    let top = rect.top;

    // Якщо вилазить за правий край екрану — показуємо ліворуч
    if(left + menuRect.width > window.innerWidth - 8){
        left = rect.left - menuRect.width - 8;
    }
    // Якщо і зліва вилазить — притискаємо до краю
    if(left < 8){
        left = 8;
    }
    // Якщо вилазить знизу — піднімаємо
    if(top + menuRect.height > window.innerHeight - 8){
        top = window.innerHeight - menuRect.height - 8;
    }

    menu.style.left = left + "px";
    menu.style.top = top + "px";
}


function randomKeywordColor(){
    // Генеруємо випадковий приємний колір (HSL -> hex),
    // щоб кожна нова група ключових слів мала свій унікальний колір за замовчуванням.
    let hue = Math.floor(Math.random() * 360);
    let s = 65, l = 50;
    let c = (1 - Math.abs(2 * l / 100 - 1)) * (s / 100);
    let x = c * (1 - Math.abs((hue / 60) % 2 - 1));
    let m = l / 100 - c / 2;
    let r, g, b;
    if (hue < 60)      { r = c; g = x; b = 0; }
    else if (hue < 120){ r = x; g = c; b = 0; }
    else if (hue < 180){ r = 0; g = c; b = x; }
    else if (hue < 240){ r = 0; g = x; b = c; }
    else if (hue < 300){ r = x; g = 0; b = c; }
    else               { r = c; g = 0; b = x; }
    let toHex = v => Math.round((v + m) * 255).toString(16).padStart(2, "0");
    return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}


function showColorPicker(mode, anchorEl){
    // mode: "single" — фарбувати лише активне слово (window.__activeWord),
    //       "multi"  — фарбувати всі слова з множинного вибору (window.__selection)
    mode = mode || "single";
    window.__colorPickerMode = mode;

    if(window.__colorPicker) hideColorPicker();

    let picker = document.createElement("div");
    picker.className = "color-picker";
    window.__colorPicker = picker;

    let applyColor = (color) => {
        if(window.__colorPickerMode === "multi"){
            addSelectionAsKeyword(color);
        } else {
            addAsKeyword(color);
        }
        hideColorPicker();
    };

    let colors = ["#3b82f6","#8b5cf6","#ec4899","#22c55e","#f97316","#eab308","#ef4444","#6b7280"];

    colors.forEach(color => {
        let dot = document.createElement("div");
        dot.className = "color-dot";
        dot.style.backgroundColor = color;
        dot.onclick = (e) => {
            e.stopPropagation();
            applyColor(color);
        };
        picker.appendChild(dot);
    });

    // Довільний колір — щоб можна було створювати необмежену кількість
    // окремих груп ключових слів, а не лише 8 попередньо заданих
    let customWrap = document.createElement("label");
    customWrap.className = "color-dot color-dot-custom";
    customWrap.title = "Свій колір";

    let customInput = document.createElement("input");
    customInput.type = "color";
    customInput.value = randomKeywordColor();
    customInput.onclick = (e) => e.stopPropagation();
    customInput.onchange = (e) => {
        applyColor(e.target.value);
    };

    customWrap.appendChild(customInput);
    picker.appendChild(customWrap);

    // Для одного слова додаємо ще й кнопку копіювання в той самий попап,
    // щоб не було окремого проміжного меню.
    if(mode === "single" && window.__activeWord){
        let activeEl = window.__activeWord;
        let divider = document.createElement("div");
        divider.className = "color-picker-divider";
        picker.appendChild(divider);

        let btnCopy = document.createElement("button");
        btnCopy.className = "color-picker-copy";
        btnCopy.type = "button";
        btnCopy.title = "Скопіювати слово";
        btnCopy.textContent = "Копіювати";
        btnCopy.onclick = (e) => {
            e.stopPropagation();
            navigator.clipboard.writeText(activeEl.textContent);
            hideColorPicker();
        };
        picker.appendChild(btnCopy);
    }

    document.body.appendChild(picker);

    // Позиціонуємо палітру поряд з активним словом/кнопкою
    let anchor = anchorEl || window.__activeWord;
    if(anchor){
        positionMenu(picker, anchor);
    }

    // Прибираємо попередній "слухач закриття", якщо він ще висить не спрацювавши
    // (наприклад, попередню палітру закрили кліком по кольору, а не кліком "назовні") —
    // інакше цей застарілий слухач одразу закриє щойно відкриту нову палітру
    // при наступному кліку по іншому слову, і здаватиметься, що не можна
    // обрати друге ключове слово.
    if(window.__colorPickerCloseHandler){
        document.removeEventListener("click", window.__colorPickerCloseHandler);
        window.__colorPickerCloseHandler = null;
    }

    let closeHandler = () => hideColorPicker();
    window.__colorPickerCloseHandler = closeHandler;

    setTimeout(() => {
        document.addEventListener("click", closeHandler, { once: true });
    }, 10);
}


function hideColorPicker(){
    if(window.__colorPicker){
        window.__colorPicker.remove();
        window.__colorPicker = null;
    }
    if(window.__colorPickerCloseHandler){
        document.removeEventListener("click", window.__colorPickerCloseHandler);
        window.__colorPickerCloseHandler = null;
    }
    if(window.__activeWord){
        window.__activeWord.classList.remove("active");
        window.__activeWord = null;
    }
}


function applyColorToWord(word, color){
    // Фарбуємо ВСІ точно такі ж слова в тексті тим самим кольором,
    // а не лише те, на яке натиснув користувач.
    // Використовуємо заздалегідь побудований індекс (word -> елементи),
    // тож не потрібно щоразу обходити весь текст — це і робить фарбування миттєвим.
    let elements = null;
    if(window.__wordIndex && window.__wordIndex.has(word)){
        elements = window.__wordIndex.get(word);
    } else {
        let resultDiv = document.getElementById("result");
        elements = resultDiv ? Array.from(resultDiv.querySelectorAll(".word")).filter(
            span => normalizeWord(span.textContent) === word
        ) : [];
    }

    elements.forEach(span => {
        if(!span || !span.classList) return;
        span.classList.remove("active");
        span.classList.remove("selected");
        span.classList.add("keyword");
        span.style.color = color;
        span.style.textShadow = `0 0 6px ${color}33`;
        span.dataset.color = color;
    });

    if(!window.__keywords) window.__keywords = {};
    window.__keywords[word] = color;
}


function addAsKeyword(color){
    let el = window.__activeWord;
    if(!el || !el.classList || !document.body.contains(el)){
        console.warn("addAsKeyword: no active word");
        return;
    }

    let word = normalizeWord(el.textContent);
    if(!word){
        window.__activeWord = null;
        return;
    }

    applyColorToWord(word, color);

    window.__activeWord = null;

    let container = document.getElementById("keyword-notes");
    if(!container) return;
    renderKeywords();
}


function addSelectionAsKeyword(color){
    if(!window.__selection || window.__selection.size === 0){
        console.warn("addSelectionAsKeyword: порожній вибір");
        return;
    }

    // Збираємо унікальні слова з усіх вибраних елементів
    // (одне й те саме слово, вибране декілька разів, додається лише раз)
    let words = new Set();
    window.__selection.forEach(el => {
        if(!el || !document.body.contains(el)) return;
        let w = normalizeWord(el.textContent);
        if(w) words.add(w);
    });

    words.forEach(w => applyColorToWord(w, color));

    clearSelection();

    let container = document.getElementById("keyword-notes");
    if(!container) return;
    renderKeywords();
}


function renderKeywords(){
    let container = document.getElementById("keyword-notes");
    if(!container) return;

    let words = Object.keys(window.__keywords);

    if(words.length === 0){
        container.innerHTML = "";
        return;
    }

    let groups = {};
    words.forEach(w => {
        let c = window.__keywords[w];
        if(!groups[c]) groups[c] = [];
        groups[c].push(w);
    });

    if(!window.__notes) window.__notes = {};
    if(!window.__conclusions) window.__conclusions = {};

    let escapeHtml = (str) => String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    container.innerHTML = Object.keys(groups).map(color => {
        let list = groups[color];
        let savedNotes = window.__notes[color] || "";
        let savedConclusion = window.__conclusions[color] || "";

        let safeNotes = escapeHtml(savedNotes);
        let safeConclusion = escapeHtml(savedConclusion);

        let heading = list.map(w => {
            let safeWord = escapeHtml(w);
            return `<span class="keyword-word" style="color:${color}; text-shadow:0 0 6px ${color}33;">${safeWord}</span>`;
        }).join(" &middot; ");

        let headingPlain = list.map(escapeHtml).join(" · ");

        return `
            <div class="keyword-group" style="--group-color:${color};">
                <h3 class="keyword-group-title">${heading}</h3>
                <textarea
                    class="keyword-group-notes"
                    data-color="${color}"
                    placeholder="Нотатки до цих ключових слів..."
                    oninput="saveGroupNotes('${color}', this.value)"
                >${safeNotes}</textarea>
                <div class="keyword-group-conclusion">
                    <h4 class="keyword-group-conclusion-title">Висновки: ${headingPlain}</h4>
                    <textarea
                        class="keyword-group-notes"
                        data-color="${color}"
                        placeholder="Ваш висновок про це ключове слово..."
                        oninput="saveGroupConclusion('${color}', this.value)"
                    >${safeConclusion}</textarea>
                </div>
            </div>
        `;
    }).join("");
}


function saveGroupNotes(color, value){
    if(!window.__notes) window.__notes = {};
    window.__notes[color] = value;
}


function saveGroupConclusion(color, value){
    if(!window.__conclusions) window.__conclusions = {};
    window.__conclusions[color] = value;
}


function showForm(){
    document.getElementById("form-section").style.display = "block";
    document.getElementById("result-section").style.display = "none";
    document.getElementById("loading-toast").classList.remove("show");
}
