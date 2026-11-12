// Прошетка низ целата страница во прелистувач: секое копче и секој екран, на ширина на телефон.
//   python prototype/build.py --site _site && python -m http.server 8765 --directory _site &
//   node tests/browser/flow.js            (бара playwright; не се извршува во дневната работа)
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 412, height: 915 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errors = [], bad = [];
  const ok = (cond, what) => { if (!cond) bad.push(what); };
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' && !/fonts\.g|ERR_|Failed to load resource/.test(m.text())) errors.push('console: ' + m.text()); });
  await page.goto(process.argv[2] || 'http://localhost:8765/'); await page.waitForTimeout(800);
  const txt = sel => page.$eval(sel, e => e.textContent.trim());
  const all = sel => page.$$eval(sel, es => es.map(e => e.textContent.trim()));
  const n = s => +s.replace(/\./g, '').replace(',', '.').replace(/[^\d.]/g, '');
  const over = async name => { const o = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth); ok(o <= 0, 'overflow ' + name + ' ' + o); };
  const small = async name => { const s = await page.evaluate(() => [...document.querySelectorAll('main button, main input[type=checkbox]:not(.cb), .actionbar button, nav button, header button')].filter(e => e.offsetParent && (e.offsetHeight < 44 || e.offsetWidth < 40)).map(e => (e.className || e.id || e.tagName) + ' ' + e.offsetWidth + 'x' + e.offsetHeight)); if (s.length) console.log('small targets', name, [...new Set(s)].slice(0, 6)); };

  // мени: седум јадења, збирот е збир на прикажаните цени
  let prices = (await all('.dishrow .side .price')).map(n);
  ok(prices.length === 7, 'seven dishes');
  ok(prices.every(p => Number.isInteger(p)), 'dish prices whole denars: ' + prices);
  ok(prices.reduce((a, b) => a + b, 0) === n(await txt('.budget .bigprice b')), 'total equals sum of dish prices');
  ok(/штедиш|Останува|Над буџетот/.test(await txt('.budget .pill')), 'budget pill');
  await over('menu'); await small('menu');
  const first = await txt('.dishrow:nth-child(1) .dishbtn b');
  await page.click('[data-swap="0"]'); ok(await txt('.dishrow:nth-child(1) .dishbtn b') !== first, 'swap changes dish');
  await page.click('[data-lock="1"]'); ok(await page.getAttribute('[data-lock="1"]', 'aria-pressed') === 'true', 'lock');
  await page.click('[data-open="2"]'); ok((await all('.parts > span')).length >= 2, 'ingredients open');
  ok((await all('.parts small')).every(t => /^акција во (Жито|КАМ|Стокомак|Рамстор), (од \d\d\.\d\d\. )?до \d\d\.\d\d\.$/.test(t)), 'ingredient promo has store and dates: ' + (await all('.parts small')).slice(0, 2));
  // поставки
  await page.click('#editBudget'); ok(await page.isVisible('#settings'), 'settings open');
  await page.click('#more'); ok(await txt('#people') === '5', 'people 5'); ok(/5 члена/i.test(await txt('.budget .cap')), 'cap shows 5');
  await page.fill('#budget', '2000'); await page.press('#budget', 'Tab'); await page.waitForTimeout(100);
  ok(n(await txt('.budget .bigprice b')) <= 2000, 'fits 2000'); ok(/2\.000/.test(await txt('.budget .of')), 'of 2000');
  await page.click('#fasting'); await page.waitForTimeout(50);
  const wed = await txt('.dishrow:nth-child(3) .tags').catch(() => ''); ok(/посно/.test(wed), 'wednesday lean: ' + wed);
  await page.click('#cardBox summary'); const cardsBefore = await txt('#cardCount'); await page.click('#cards .chip'); ok(await txt('#cardCount') !== cardsBefore, 'card toggle');
  await page.click('#cards .chip');
  await page.click('#favBox summary'); const favBefore = await txt('#favCount'); await page.click('#favs .chip[aria-pressed=false]'); ok(await txt('#favCount') !== favBefore, 'fav toggle');
  await small('settings');
  await page.click('#settingsBtn'); ok(!(await page.isVisible('#settings')), 'settings closed');
  // акции на почетната: маркет и датуми
  const teaser = await all('#teaser .pmini small'); ok(teaser.length > 0 && teaser.every(t => /^(Жито|КАМ|Стокомак|Рамстор) · (од \d\d\.\d\d\. )?до \d\d\.\d\d\.$/.test(t)), 'teaser store+dates ' + teaser[0]);
  // избор на јадења
  await page.click('#view-menu [data-go="dishes"]'); await page.click('[data-day="5"]');
  const pick = await txt('#dishList .dish:nth-child(4) .dishbtn b'); await page.click('#dishList .dish:nth-child(4) [data-put]');
  await page.fill('#dq', 'пита'); await page.waitForTimeout(100); ok((await all('#dishList .dish')).length >= 2, 'dish search');
  await page.fill('#dq', ''); await page.click('[data-kind="*posno"]'); ok((await all('#dishList .dish .tags')).every(t => /посно/.test(t)), 'posno filter');
  await page.click('[data-dopen]'); ok((await all('#dishList .parts > span')).length >= 2, 'dish ingredients'); await over('dishes'); await small('dishes');
  await page.click('#actionbar [data-go="menu"]');
  ok(await txt('.dishrow:nth-child(6) .dishbtn b') === pick, 'picked dish on saturday'); ok(/твој избор/.test(await txt('.dishrow:nth-child(6) .tags')), 'marked as own pick');
  // следна недела
  await page.click('#next'); await page.waitForTimeout(100); ok(/недела 2/.test(await txt('#weekTitle')), 'week 2'); ok((await page.$$('[data-lock][aria-pressed=true]')).length === 0, 'locks cleared');
  // акции
  await page.click('[data-tab="promos"]'); ok(/важечки · \d+ најевтини/.test(await txt('#promoStats')), 'promo stats');
  let meta = await all('.promo .pmeta'); ok(meta.length === 30, '30 promos shown'); ok(meta.every(t => /^(Жито|КАМ|Стокомак|Рамстор) · (од \d\d\.\d\d\. )?до \d\d\.\d\d\.$/.test(t)), 'promo store+dates');
  console.log('promos without start date in first 30:', meta.filter(t => !/ од /.test(t)).length);
  await page.click('[data-pc="kam"]').catch(async () => { const v = await page.$$eval('[data-pc]', es => es.map(e => e.dataset.pc)); console.log('chains', v); await page.click(`[data-pc="${v[2]}"]`); });
  meta = await all('.promo .pmeta'); ok(meta.length > 0 && new Set(meta.map(t => t.split(' · ')[0])).size === 1, 'chain filter: ' + [...new Set(meta.map(t => t.split(' · ')[0]))]);
  await page.click('[data-pc=""]'); await page.click('#onlyBest'); ok((await all('.promo')).length === (await all('.promo .strip.ok')).filter(t => /Најевтино во/.test(t)).length, 'only best');
  await page.click('#onlyBest'); await page.click('#noCard'); ok((await all('.promo .strip')).every(t => !/Со картичка/.test(t)), 'no card'); await page.click('#noCard');
  await page.click('#morePromos'); ok((await all('.promo')).length === 70, 'more promos');
  const bar = await txt('#actionbar .primary'); await page.click('.promo [data-add]'); ok(/На листа/.test(await txt('.promo [data-add]')) && await txt('#actionbar .primary') !== bar, 'promo added to list');
  await over('promos'); await small('promos');
  // цени
  await page.click('[data-tab="prices"]'); await page.fill('#q', 'млеко'); await page.waitForTimeout(150);
  ok((await all('#needResults .row')).length >= 1 && (await all('#productResults .row')).length >= 3, 'price search');
  await page.click('#needResults [data-watch]'); ok(await page.getAttribute('#needResults [data-watch]', 'aria-pressed') === 'true', 'watch on');
  await page.fill('#q', ''); await page.click('[data-ng]'); ok((await all('#needResults .row')).length >= 3, 'group filter'); await over('prices'); await small('prices');
  // листа
  await page.click('[data-tab="list"]'); const rows = (await all('#items label.lrow')).length; ok(new RegExp('^' + rows + ' ставки').test(await txt('#listSub')), 'list count ' + rows + ' / ' + await txt('#listSub'));
  ok(/ден\. на каса/.test(await txt('#bestStore')), 'best store card');
  await page.click('#whereBtn'); ok((await all('#stores .row')).length >= 4, 'store comparison'); await page.click('#whereBtn'); ok(!(await page.isVisible('#stores')), 'comparison closes');
  const own = await page.$('#items [data-own][data-step="1"]'); ok(!!own, 'own item has stepper');
  const q0 = await page.$eval('#items [data-own]', e => e.closest('.lrow').querySelector('.qty').textContent); await page.click('#items [data-own][data-step="1"]');
  ok(await page.$eval('#items [data-own]', e => e.closest('.lrow').querySelector('.qty').textContent) !== q0, 'stepper changes quantity');
  ok((await page.$$('#items .cb:checked')).length === 0, 'stepper does not tick the row');
  await page.click('#items [data-reg]'); ok(/1 ставка се додава/.test(await txt('#regular')), 'regular item: ' + (await txt('#regular')).slice(0, 60));
  await page.click('#clearRegular'); await page.click('#addBasics'); ok(/ставки се додаваат/.test(await txt('#regular')), 'basics added');
  await page.click('#items .cb'); ok(/1 купени/.test(await txt('#listSub')), 'ticked'); ok((await page.$$('#items .lrow.done')).length === 1, 'done row'); await over('list'); await small('list');
  await page.click('#copy'); await page.waitForTimeout(200);
  // во маркет
  await page.click('#actionbar [data-go="store"]'); ok((await all('#storeItems .srow')).length === (await all('#storeItems .srow')).length && /^1 од/.test(await txt('#storeSub')), 'store mode');
  await page.click('#storeItems .srow:not(.done) .cb'); ok(/^2 од/.test(await txt('#storeSub')), 'store tick'); await over('store');
  await page.click('#actionbar [data-go="list"]'); ok((await page.$$('#items .lrow.done')).length === 2, 'ticks carried back');
  await page.click('#clearDone'); ok((await page.$$('#items .lrow.done')).length === 0, 'unticked');
  // алатки
  await page.click('[data-tab="tools"]'); ok(!(await page.isVisible('#actionbar')), 'no action bar in tools');
  ok((await all('#watchList .row')).length === 1, 'watch row');
  await page.fill('#caP', '60'); await page.fill('#caQ', '500'); await page.fill('#cbP', '100'); await page.fill('#cbQ', '1000'); ok(/Б е поевтино за 17%/.test(await txt('#calcOut')), 'calc: ' + await txt('#calcOut'));
  await page.fill('#spentIn', '1540'); await page.click('#spentAdd'); ok(/1\.540 ден\./.test(await txt('#spentList')), 'spent');
  await page.click('#haveBox summary'); await page.click('#haveChips .chip'); await page.click('#haveChips .chip:nth-child(5)'); ok((await all('#cookResults .row')).length >= 1, 'cook suggestions');
  const cook = await page.$('#cookResults [data-cook]'); if (cook) { await cook.click(); ok(/На листа/.test(await txt('#cookResults [data-cook]')), 'cook add'); }
  await over('tools'); await small('tools');
  // памтење и почни одново
  await page.reload(); await page.waitForTimeout(600); ok(await page.isVisible('#view-tools'), 'tab remembered'); await page.click('[data-tab="menu"]'); ok(/недела 2/.test(await txt('#weekTitle')), 'week remembered'); await page.click('#reset'); ok(/недела 1/.test(await txt('#weekTitle')), 'reset');
  console.log('failed checks:', JSON.stringify(bad, null, 1));
  console.log('errors:', JSON.stringify(errors));
  await browser.close();
})();
