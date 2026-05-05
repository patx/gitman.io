% rebase("base.tpl", title="#" + str(pr["number"]) + " " + pr["title"], user=user, error=error, notice=notice)

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
      <h2>(#{{pr["number"]}}) {{pr["title"]}}</h2>
      <p class="muted"><strong>{{pr["status"]}}</strong> <small>(created by <a href="/{{pr["author_username"]}}">{{pr["author_username"]}}</a> on {{pr["created_at"]}})</small></p>
      <p class="muted"><a href="/{{pr["source_owner_username"]}}/{{pr["source_repo_name"]}}">{{pr["source_owner_username"]}}/{{pr["source_repo_name"]}}</a> into <a href="/{{pr["target_owner_username"]}}/{{pr["target_repo_name"]}}">{{pr["target_owner_username"]}}/{{pr["target_repo_name"]}}</a></p>
      <p class="muted">{{format_ref_label(pr["source_ref_type"], pr["source_ref_name"])}} into {{format_ref_label(pr["target_ref_type"], pr["target_ref_name"])}}</p>
    </div>
    % if can_maintain and pr["status"] == "open":
      <div class="filters">
        <form method="post">
          {{!csrf_field()}}
          <input type="hidden" name="action" value="merge">
          <button class="button" type="submit">Merge</button>
        </form>
        <form method="post">
          {{!csrf_field()}}
          <input type="hidden" name="action" value="close">
          <button class="button secondary small" type="submit">Close</button>
        </form>
      </div>
    % end
  </div>
  % if pr["body"]:
    <pre class="readme">{{pr["body"]}}</pre>
  % else:
    <p class="empty">No description.</p>
  % end
  % if pr["status"] == "merged":
    <p class="notice">Merged by {{pr["merged_by_username"] or "unknown"}} on {{pr["merged_at"]}} as <code>{{pr["merge_node"]}}</code>.</p>
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
    <p><a href="/login?next=/{{repo['owner_username']}}/{{repo['name']}}/pulls/{{pr['number']}}">Log in to comment</a></p>
  % end
</section>

<section class="panel">
  <h2>Diff</h2>
  <p class="muted">Base <code>{{pr["base_node"]}}</code> to {{format_ref_label(pr["source_ref_type"], pr["source_ref_name"])}} <code>{{current_source_node}}</code></p>
  % if diff_error:
    <p class="alert">{{diff_error}}</p>
  % elif diff:
    <pre class="diff"><code class="language-diff">{{diff}}</code></pre>
  % else:
    <p class="empty">No diff for this pull request.</p>
  % end
</section>
