$(document).ready(() => {
    
    $("#manual-file-upload-btn").click(() => {

        // Upload the image
        var input = document.querySelector('#manual-upload-file-input')
        
        var formdata = new FormData();
        formdata.append("file", input.files[0]);

        var requestOptions = {
            method: 'POST',
            body: formdata,
            redirect: 'follow'
        };

        fetch("/api/manual-prediction", requestOptions)
            .then(response => response.blob())
            .then(imageBlob => {
                
                // Display the image result
                const imageObjectURL = URL.createObjectURL(imageBlob);
                document.querySelector("#uploaded-image-result").src = imageObjectURL;
                console.log(imageObjectURL);
            })
            .catch(error => console.log('error', error));

    });
  
});