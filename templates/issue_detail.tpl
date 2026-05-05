% rebase("base.tpl", title="#" + str(issue["number"]) + " " + issue["title"], user=user, error=error, notice=notice)

<section class="repo-header slim">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)

    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)

  </div>
</section>

<section class="panel">
  <div class="panel-heading">
    <div>
      <h2>(#{{issue["number"]}}) {{issue["title"]}}</h2>
      <p class="muted"><strong>{{issue["status"]}}</strong> by {{issue["author_username"]}} on {{issue["created_at"]}}</p>
    </div>
    % if can_maintain:
      <form method="post">
        {{!csrf_field()}}
        % if issue["status"] == "open":
          <input type="hidden" name="action" value="close">
          <button class="button secondary small" type="submit">Close issue</button>
        % else:
          <input type="hidden" name="action" value="reopen">
          <button class="button secondary small" type="submit">Reopen issue</button>
        % end
      </form>
    % end
  </div>
  % if issue["body"]:
    <span>{{issue["body"]}}</span>
  % else:
    <p class="empty">No description.</p>
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
    <p><a href="/login?next=/{{repo['owner_username']}}/{{repo['name']}}/issues/{{issue['number']}}">Log in to comment</a></p>
  % end
</section>
