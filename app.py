import streamlit as st
import mindsdb_sdk
import pandas as pd
from urllib.parse import urlparse, parse_qs
import matplotlib.pyplot as plt

# Connect to the specified host and port
server = mindsdb_sdk.connect("http://49.13.27.8:47334")
print("connecting")
# Get the MindsDB project
mindsdb = server.get_project("mindsdb")


def extract_video_id(youtube_url):
    """Extract the video ID from a YouTube URL."""
    parsed_url = urlparse(youtube_url)
    if parsed_url.hostname == "youtu.be":
        return parsed_url.path[1:]
    if parsed_url.hostname in ("www.youtube.com", "youtube.com"):
        if parsed_url.path == "/watch":
            return parse_qs(parsed_url.query)["v"][0]
        if parsed_url.path.startswith("/embed/"):
            return parsed_url.path.split("/")[2]
        if parsed_url.path.startswith("/v/"):
            return parsed_url.path.split("/")[2]
    return None


# Preloaded YouTube URL
preloaded_url = "https://www.youtube.com/watch?v=AxSK444-gnM"

# Create a form for user input
with st.form(key="video_form"):
    youtube_url = st.text_input("Enter YouTube URL", preloaded_url)
    submit_button = st.form_submit_button(label="Submit")

if submit_button:
    video_id = extract_video_id(youtube_url)

    if video_id:
        # Query the comments and their sentiment and topics based on the video ID
        data_handlers = mindsdb.query(
            f"""
            SELECT t.comment, m.topic, s.sentiment, t.channel_id 
            FROM mindsdb_youtube.comments AS t 
            JOIN mindsdb.topic_classifier_model AS m 
            JOIN mindsdb.sentiment_classifier_model as s 
            WHERE t.video_id = '{video_id}' 
            LIMIT 100;
        """
        ).fetch()
        print("fetched")
        # Convert the results to a DataFrame with specific fields
        data_handlers_df = pd.DataFrame(
            data_handlers, columns=["comment", "topic", "sentiment", "channel_id"]
        )

        if not data_handlers_df.empty:
            # Get the channel ID from the first row
            channel_id = data_handlers_df["channel_id"].iloc[0]

            # Query the channel description based on the channel ID
            channel_description = mindsdb.query(
                f'SELECT title, description, subscriber_count, video_count FROM mindsdb_youtube.channels WHERE channel_id="{channel_id}"'
            ).fetch()

            # Convert the results to a DataFrame with specific fields
            channel_description_df = pd.DataFrame(
                channel_description,
                columns=["title", "description", "subscriber_count", "video_count"],
            )

            # Extract channel information
            if not channel_description_df.empty:
                channel_info = channel_description_df.iloc[0]

                # Display the results in Streamlit
                st.title("YouTube Video Analysis")

                # YouTube-like layout for channel information
                st.header(channel_info["title"])
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Subscribers:** {channel_info['subscriber_count']}")
                with col2:
                    st.write(f"**Videos:** {channel_info['video_count']}")

                description = channel_info["description"]
                max_lines = 3
                short_description = "\n".join(description.split("\n")[:max_lines]) + (
                    "..." if len(description.split("\n")) > max_lines else ""
                )
                st.write(f"**Description:** {short_description}")

            # Filter for only positive, negative, and neutral sentiments
            filtered_df = data_handlers_df[
                data_handlers_df["sentiment"].isin(["positive", "neutral", "negative"])
            ]

            # Calculate sentiment percentages
            sentiment_counts = (
                filtered_df["sentiment"].value_counts(normalize=True) * 100
            )
            sentiment_labels = sentiment_counts.index
            sentiment_values = sentiment_counts.values

            # Plot sentiment pie chart
            fig1, ax1 = plt.subplots(figsize=(4, 4))
            ax1.pie(
                sentiment_values,
                labels=sentiment_labels,
                autopct="%1.1f%%",
                colors=["#66b3ff", "#ff6666", "#99ff99"],
            )
            ax1.axis(
                "equal"
            )  # Equal aspect ratio ensures the pie is drawn as a circle.

            # Calculate trending topics
            topic_counts = filtered_df["topic"].value_counts().head(10)

            # Plot trending topics bar chart
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.bar(topic_counts.index, topic_counts.values, color="skyblue")
            ax2.set_xlabel("Topics")
            ax2.set_ylabel("Frequency")
            ax2.set_title("Trending Topics")
            ax2.set_xticklabels(topic_counts.index, rotation=45, ha="right")

            col1, col2 = st.columns(2)
            with col1:
                st.header("Sentiment Distribution")
                st.pyplot(fig1)
            with col2:
                st.header("Trending Topics")
                st.pyplot(fig2)

            # Adjust index to start from 1
            filtered_df.index = filtered_df.index + 1

            st.header("Comments with Sentiment and Topic Classification")
            st.dataframe(filtered_df[["comment", "topic", "sentiment"]])
        else:
            st.write("No data found for this video.")
    else:
        st.write("Invalid YouTube URL.")
