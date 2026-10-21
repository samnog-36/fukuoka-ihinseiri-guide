(() => {
  const extra = {
    remote: ['鍵の受渡し方法、立会いの代替、作業前後の写真報告、残す物の返送方法を確認する'],
    stairs: ['階数、エレベーター、通路幅、駐車位置を伝え、搬出・養生の追加条件を書面で確認する'],
    keep: ['残す物・探す物を写真付きで共有し、処分前に確認する手順を決める'],
    appliance: ['家具・家電の種類と個数を伝え、取外し・搬出・処分が見積もりに含まれるか確認する'],
    deadline: ['退去などの期限、作業可能日、鍵の返却日、遅延時の対応を確認する']
  };
  const base = ['作業範囲・対象の部屋・物量を写真や一覧で整理する','複数の見積もりを同じ作業条件で比較する','処分方法は地域の公式案内を確認する'];
  document.getElementById('preparation').addEventListener('change', () => {
    const rows = [...base];
    document.querySelectorAll('#preparation input:checked').forEach(x => rows.push(...extra[x.value]));
    const list = document.getElementById('preparation-results');list.replaceChildren();
    rows.forEach(text => {const li=document.createElement('li');li.textContent=text;list.append(li);});
  });
  ['税込総額','含まれる作業・対象品','搬出・階段・養生','追加料金が発生する条件','処分を担当する事業者と確認先','買取額と作業費の区別','残す物・探索・作業報告','作業日・支払日・キャンセル条件'].forEach(label => {
    const tr=document.createElement('tr'),th=document.createElement('th');th.scope='row';th.textContent=label;tr.append(th);
    ['A社','B社'].forEach(company => {const td=document.createElement('td'),input=document.createElement('textarea');input.rows=2;input.style.width='100%';input.style.minWidth='130px';input.setAttribute('aria-label',company+' '+label);td.append(input);tr.append(td);});
    document.getElementById('comparison-rows').append(tr);
  });
  document.getElementById('print-checklist').addEventListener('click',()=>window.print());
})();
