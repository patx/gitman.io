% rebase("base.tpl", title="New issue", user=user, error=error, notice=notice)

<section class="repo-header slim">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)
    
    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)
    
  </div>
</section>

<section class="panel">
  <h2>Open a new issue</h2>
  <form method="post">
    {{!csrf_field()}}
    <label>
      Title
      <input name="title" value="{{title_value}}" required maxlength="200">
    </label>
    <label>
      Body
      <textarea name="body" rows="8">{{body_value}}</textarea>
    </label>
    <button class="button" type="submit">Open issue</button>
  </form>
</section>
