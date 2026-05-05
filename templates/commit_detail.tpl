% rebase("base.tpl", title=commit["short_node"] + " at " + repo["owner_username"] + "/" + repo["name"], user=user, error=error, notice=notice)

<section class="repo-header slim">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)
    
    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)

  </div>
</section>

<section class="panel">
  <h2>{{commit["description"].splitlines()[0] if commit["description"] else commit["short_node"]}}</h2>
  <p class="muted">Commit {{commit["short_node"]}} · {{commit["author"]}} · {{commit["date"]}}</p>
  <dl class="meta-list">
    <dt>Changeset</dt>
    <dd>
      <code>{{commit["node"]}}</code>
    </dd>
    % if commit["parents"]:
      <dt>Parents</dt>
      <dd><code>{{commit["parents"]}}</code></dd>
    % end
  </dl>
  <p class="muted"><a href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/src', commit_source_ref, True)}}">View source at this commit</a></p>
  % if "\n" in commit["description"]:
    <pre class="readme">{{commit["description"]}}</pre>
  % end
</section>

<section class="panel">
  <h2>Comments</h2>
  % if comments:
    <div class="comment-list">
      % for comment in comments:
        <article class="comment">
            <p><strong><a href="/{{comment["author_username"]}}">@{{comment["author_username"]}}</a>:</strong> {{!render_markdown_links(comment["body"])}} <small class="muted">{{comment["created_at"]}}</small></p>
        </article>
      % end
    </div>
  % else:
    <p class="empty">No comments yet.</p>
  % end

  % if user:
    <form method="post">
      {{!csrf_field()}}
      <input type="hidden" name="action" value="comment">
      <label>
        Add a comment
        <textarea name="body" rows="5">{{comment_value}}</textarea>
      </label>
      <button class="button" type="submit">Comment</button>
    </form>
  % else:
    <p><a href="/login?next=/{{repo['owner_username']}}/{{repo['name']}}/commits/{{commit['node']}}">Log in to comment</a></p>
  % end
</section>

<section class="panel">
  <h2>Diff</h2>
  % if diff:
    <pre class="diff"><code class="language-diff">{{diff}}</code></pre>
  % else:
    <p class="empty">No diff for this commit.</p>
  % end
</section>
