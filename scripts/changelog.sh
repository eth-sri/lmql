# get all commits since last tag
# and format them as markdown

# get second last tag
tag=$(git describe --abbrev=0 --tags $(git rev-list --tags --skip=1 --max-count=1))

# get all commits since last tag
commits=$(git log --pretty=format:"%s" $tag..HEAD)

echo "Building changelog since $tag"

# format commits as markdown
echo "$commits" | sed -e 's/^/- /'