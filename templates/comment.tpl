<article class="comment">
  <header class="comment-meta">
    <strong><a href="/{{comment["author_username"]}}">@{{comment["author_username"]}}</a></strong>
    <small class="muted">{{comment["created_at"]}}</small>
  </header>
  <div class="comment-body markdown-body">{{!render_markdown(comment["body"])}}</div>
</article>
