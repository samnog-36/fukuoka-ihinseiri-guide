/**
 * 福岡遺品整理ガイド - 記事検索機能
 * 静的サイト用クライアントサイド検索
 */
(function() {
  'use strict';

  let articles = [];
  let searchLoaded = false;

  // 検索データの読み込み
  function loadSearchData() {
    if (searchLoaded) return Promise.resolve();
    return fetch('/js/search-data.json')
      .then(function(res) { return res.json(); })
      .then(function(data) {
        articles = data;
        searchLoaded = true;
      })
      .catch(function(err) {
        console.error('検索データの読み込みに失敗しました:', err);
      });
  }

  // 検索実行
  function search(query) {
    if (!query || query.trim().length === 0) return [];
    
    var terms = query.toLowerCase().trim().split(/\s+/);
    var results = [];
    
    for (var i = 0; i < articles.length; i++) {
      var article = articles[i];
      var searchText = (article.title + ' ' + article.desc + ' ' + article.keywords + ' ' + article.category).toLowerCase();
      
      var matchCount = 0;
      for (var j = 0; j < terms.length; j++) {
        if (searchText.indexOf(terms[j]) !== -1) {
          matchCount++;
        }
      }
      
      if (matchCount > 0) {
        results.push({
          article: article,
          score: matchCount / terms.length
        });
      }
    }
    
    // スコア順にソート
    results.sort(function(a, b) { return b.score - a.score; });
    return results.slice(0, 20);
  }

  // 検索結果のHTML生成
  function renderResults(results, container) {
    if (results.length === 0) {
      container.innerHTML = '<div class="search-no-results"><p>該当する記事が見つかりませんでした。<br>別のキーワードでお試しください。</p></div>';
      return;
    }
    
    var html = '<div class="blog-grid">';
    for (var i = 0; i < results.length; i++) {
      var a = results[i].article;
      var imgSrc = a.thumbnail || '/images/blog/default-thumb.webp';
      html += '<article class="blog-card">';
      html += '<a href="' + a.url + '">';
      html += '<div class="blog-card-image"><img src="' + imgSrc + '" alt="' + a.title + '" loading="lazy"></div>';
      html += '<div class="blog-card-content">';
      html += '<span class="blog-card-category">' + a.category + '</span>';
      html += '<h3 class="blog-card-title">' + a.title + '</h3>';
      html += '<p class="blog-card-excerpt">' + a.desc + '</p>';
      html += '<time class="blog-card-date">' + a.date + '</time>';
      html += '</div></a></article>';
    }
    html += '</div>';
    container.innerHTML = html;
  }

  // 検索イベントのバインド
  function initSearch() {
    var searchInput = document.getElementById('blog-search-input');
    var searchBtn = document.getElementById('blog-search-btn');
    var resultsContainer = document.getElementById('search-results');
    
    if (!searchInput || !resultsContainer) return;
    
    var originalContent = null;
    var blogGrid = document.querySelector('.blog-grid');
    if (blogGrid) {
      originalContent = blogGrid.parentElement;
    }
    
    var debounceTimer = null;
    
    function doSearch() {
      var query = searchInput.value.trim();
      if (query.length === 0) {
        resultsContainer.innerHTML = '';
        resultsContainer.style.display = 'none';
        if (originalContent) originalContent.style.display = '';
        return;
      }
      
      loadSearchData().then(function() {
        var results = search(query);
        resultsContainer.style.display = 'block';
        if (originalContent && results.length > 0) {
          originalContent.style.display = 'none';
        }
        renderResults(results, resultsContainer);
      });
    }
    
    searchInput.addEventListener('input', function() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(doSearch, 300);
    });
    
    searchInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        clearTimeout(debounceTimer);
        doSearch();
      }
    });
    
    if (searchBtn) {
      searchBtn.addEventListener('click', function(e) {
        e.preventDefault();
        doSearch();
      });
    }
  }

  // DOM読み込み完了後に初期化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSearch);
  } else {
    initSearch();
  }
})();
